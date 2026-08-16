import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright


BASE_URL = "https://www.card-gorilla.com"
LIST_URL = f"{BASE_URL}/search/card"
OUTPUT_FILE = Path("cards.json")


async def collect_card_links(page):
    """
    현재 페이지에 표시되어 있는 카드 상세 URL을 전부 수집한다.
    """

    links = await page.locator('a[href*="/card/detail/"]').evaluate_all(
        """
        elements => elements
            .map(a => a.href)
            .filter(href => /\\/card\\/detail\\/\\d+/.test(href))
        """
    )

    result = set()

    for url in links:
        match = re.search(r"/card/detail/(\d+)", url)

        if match:
            card_id = match.group(1)
            result.add(
                f"{BASE_URL}/card/detail/{card_id}"
            )

    return result


async def scroll_to_bottom(page):
    """
    페이지를 천천히 아래까지 내려서
    lazy loading 되어 있는 카드들을 화면에 표시한다.
    """

    previous_height = 0
    stable_count = 0

    for _ in range(30):

        current_height = await page.evaluate(
            "document.body.scrollHeight"
        )

        await page.evaluate(
            "window.scrollTo(0, document.body.scrollHeight)"
        )

        await page.wait_for_timeout(800)

        new_height = await page.evaluate(
            "document.body.scrollHeight"
        )

        if new_height == previous_height:
            stable_count += 1
        else:
            stable_count = 0

        previous_height = new_height

        if stable_count >= 3:
            break


async def click_more_button(page):
    """
    '카드 더보기'라는 텍스트를 가진 실제 DOM 요소를 찾는다.

    특정 CSS selector에 의존하지 않는다.
    """

    result = await page.evaluate(
        """
        () => {
            const elements = Array.from(
                document.querySelectorAll("button, a, div, span")
            );

            const candidates = elements.filter(el => {
                const text = (el.innerText || "").trim();

                return text === "카드 더보기" ||
                       text.includes("카드 더보기");
            });

            if (candidates.length === 0) {
                return false;
            }

            // 가장 작은 요소를 우선 선택
            candidates.sort((a, b) => {
                return a.getBoundingClientRect().height
                     - b.getBoundingClientRect().height;
            });

            const target = candidates[0];

            target.scrollIntoView({
                behavior: "instant",
                block: "center"
            });

            target.click();

            return true;
        }
        """
    )

    return result


async def crawl_all_cards(page):
    """
    카드고릴라 전체 카드 URL 수집
    """

    print("=" * 60)
    print("카드고릴라 전체 카드 크롤링 시작")
    print("=" * 60)

    print()
    print("카드 목록 페이지 접속")

    await page.goto(
        LIST_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    await page.wait_for_timeout(3000)

    print("페이지 로딩 완료")

    all_cards = set()

    previous_count = 0
    no_change_count = 0

    for round_no in range(1, 101):

        # 화면 아래까지 이동
        await scroll_to_bottom(page)

        # 현재 카드 링크 수집
        current_cards = await collect_card_links(page)

        before = len(all_cards)

        all_cards.update(current_cards)

        after = len(all_cards)

        print(
            f"{round_no}회차 - "
            f"현재 페이지 카드: {len(current_cards)}개 / "
            f"전체 발견: {after}개"
        )

        # 카드 수가 증가하지 않았는지 확인
        if after == previous_count:
            no_change_count += 1
        else:
            no_change_count = 0

        previous_count = after

        # 충분히 반복했는데 더 이상 증가하지 않으면 종료
        if no_change_count >= 3:
            print()
            print("새로운 카드가 더 이상 발견되지 않아 종료합니다.")
            break

        # 카드 더보기 클릭
        clicked = await click_more_button(page)

        if clicked:
            print("카드 더보기 클릭")

            # 새로운 카드가 로딩될 시간
            await page.wait_for_timeout(1500)

        else:
            print("카드 더보기 요소를 찾지 못했습니다.")

            # 혹시 lazy loading 때문에 아직 안 잡혔을 수 있으므로
            # 한 번 더 기다린다.
            await page.wait_for_timeout(1000)

            clicked_again = await click_more_button(page)

            if clicked_again:
                print("카드 더보기 재탐색 성공")
                await page.wait_for_timeout(1500)
            else:
                # 카드 수가 계속 유지되면 종료
                if no_change_count >= 1:
                    print("더 이상 추가할 카드가 없는 것으로 판단합니다.")
                    break

    return all_cards


async def get_card_detail(page, url):
    """
    카드 상세 페이지에서 기본 정보 수집
    """

    card_id_match = re.search(r"/card/detail/(\d+)", url)

    if not card_id_match:
        return None

    card_id = card_id_match.group(1)

    print(f"카드 상세 수집: {card_id}")

    try:
        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(1000)

        title = await page.title()

        # 페이지에서 카드명을 찾는다.
        card_name = ""

        selectors = [
            "h1",
            "h2",
            "h3",
            ".card_name",
            ".card-name",
            "[class*='card_name']",
            "[class*='card-name']",
        ]

        for selector in selectors:

            locator = page.locator(selector)

            count = await locator.count()

            if count > 0:

                for i in range(min(count, 5)):

                    text = (await locator.nth(i).inner_text()).strip()

                    if text and len(text) > 1:
                        card_name = text
                        break

            if card_name:
                break

        return {
            "card_id": card_id,
            "card_name": card_name,
            "card_url": url,
            "page_title": title,
        }

    except Exception as e:

        print(
            f"상세 페이지 수집 실패 "
            f"{card_id}: {e}"
        )

        return {
            "card_id": card_id,
            "card_name": "",
            "card_url": url,
            "page_title": "",
        }


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            viewport={
                "width": 1440,
                "height": 1200
            },
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()

        # -----------------------------
        # 1. 전체 카드 URL 수집
        # -----------------------------

        card_urls = await crawl_all_cards(page)

        card_urls = sorted(
            card_urls,
            key=lambda url: int(
                re.search(r"/card/detail/(\d+)", url).group(1)
            )
        )

        print()
        print("=" * 60)
        print(f"전체 카드 ID: {len(card_urls)}개")
        print("=" * 60)

        # -----------------------------
        # 2. 상세 페이지 수집
        # -----------------------------

        cards = []

        for index, url in enumerate(card_urls, start=1):

            print(
                f"[{index}/{len(card_urls)}] {url}"
            )

            detail = await get_card_detail(
                page,
                url
            )

            if detail:
                cards.append(detail)

        # -----------------------------
        # 3. JSON 저장
        # -----------------------------

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                cards,
                f,
                ensure_ascii=False,
                indent=2
            )

        print()
        print("=" * 60)
        print(f"cards.json 저장 완료: {len(cards)}개")
        print("=" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
