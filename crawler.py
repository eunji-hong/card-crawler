import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright


# ============================================================
# 설정
# ============================================================

BASE_URL = "https://www.card-gorilla.com"
CARD_LIST_URL = "https://www.card-gorilla.com/search/card"

OUTPUT_FILE = Path("cards.json")


# ============================================================
# 카드 ID 추출
# ============================================================

def extract_card_id(url):
    """
    /card/detail/3016
    형태에서 카드 ID를 추출
    """

    match = re.search(r"/card/detail/(\d+)", url)

    if match:
        return match.group(1)

    return None


# ============================================================
# 카드 목록 수집
# ============================================================

async def collect_card_links(page):

    print("카드고릴라 카드 목록 페이지 접속")

    await page.goto(
        CARD_LIST_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    print("페이지 로딩 완료")

    # 페이지가 실제로 로딩될 시간을 줌
    await page.wait_for_timeout(3000)

    card_ids = set()

    # --------------------------------------------------------
    # 현재 카드 링크 추출
    # --------------------------------------------------------

    async def collect_current_cards():

        links = await page.locator(
            'a[href*="/card/detail/"]'
        ).evaluate_all(
            """
            elements => elements.map(e => ({
                href: e.href,
                text: e.innerText
            }))
            """
        )

        before = len(card_ids)

        for item in links:

            card_id = extract_card_id(item["href"])

            if card_id:
                card_ids.add(card_id)

        after = len(card_ids)

        return after - before


    # --------------------------------------------------------
    # 처음 카드 수집
    # --------------------------------------------------------

    await collect_current_cards()

    print(f"현재 발견 카드: {len(card_ids)}개")


    # --------------------------------------------------------
    # 카드 더보기 반복
    # --------------------------------------------------------

    max_click = 200

    for click_count in range(max_click):

        before_count = len(card_ids)

        # 현재 카드 수집
        await collect_current_cards()

        # ----------------------------------------------------
        # 카드 더보기 버튼 찾기
        # ----------------------------------------------------

        more_button = page.get_by_text(
            "카드 더보기",
            exact=True
        )

        count = await more_button.count()

        if count == 0:

            print("카드 더보기 버튼을 찾지 못했습니다.")

            break


        # ----------------------------------------------------
        # 첫 번째 버튼 확인
        # ----------------------------------------------------

        button = more_button.first

        try:

            await button.scroll_into_view_if_needed()

            await page.wait_for_timeout(500)

            print(
                f"카드 더보기 클릭 "
                f"({click_count + 1}회)"
            )

            await button.click(
                timeout=10000
            )

        except Exception as e:

            print(
                f"카드 더보기 클릭 실패: {e}"
            )

            break


        # ----------------------------------------------------
        # 카드 추가 로딩 대기
        # ----------------------------------------------------

        try:

            await page.wait_for_function(
                """
                (oldCount) => {
                    return document.querySelectorAll(
                        'a[href*="/card/detail/"]'
                    ).length > oldCount;
                }
                """,
                arg=before_count,
                timeout=10000
            )

        except Exception:

            # 카드가 추가되지 않았을 수도 있으므로
            # 잠시 기다린 후 다시 확인
            await page.wait_for_timeout(2000)


        # ----------------------------------------------------
        # 새 카드 수집
        # ----------------------------------------------------

        await collect_current_cards()

        after_count = len(card_ids)

        print(
            f"현재 발견 카드: {after_count}개"
        )


        # ----------------------------------------------------
        # 더 이상 카드가 늘어나지 않으면 종료
        # ----------------------------------------------------

        if after_count == before_count:

            print(
                "새로운 카드가 추가되지 않아 "
                "크롤링을 종료합니다."
            )

            break


    return sorted(
        card_ids,
        key=lambda x: int(x)
    )


# ============================================================
# 카드 상세 정보
# ============================================================

async def collect_card_detail(page, card_id):

    url = f"{BASE_URL}/card/detail/{card_id}"

    try:

        print(f"카드 상세 수집: {card_id}")

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(1000)

        # 페이지 전체 텍스트
        text = await page.locator("body").inner_text()

        # ----------------------------------------------------
        # 카드명
        # ----------------------------------------------------

        card_name = ""

        # title 우선
        title = await page.title()

        if title:
            card_name = title.strip()

        # title에 불필요한 사이트명이 붙는 경우 제거
        card_name = re.sub(
            r"\s*\|\s*카드고릴라.*$",
            "",
            card_name
        ).strip()

        # ----------------------------------------------------
        # 카드사
        # ----------------------------------------------------

        card_company = ""

        # 페이지에서 흔히 보이는 카드사 목록
        companies = [
            "신한카드",
            "삼성카드",
            "현대카드",
            "KB국민카드",
            "롯데카드",
            "우리카드",
            "하나카드",
            "NH농협카드",
            "IBK기업은행",
            "BC카드",
            "BC바로카드",
            "씨티카드",
            "전북은행",
            "광주은행",
            "제주은행",
            "수협은행",
            "DGB대구은행",
            "BNK부산은행",
            "BNK경남은행"
        ]

        for company in companies:

            if company in text:

                card_company = company
                break


        return {
            "card_id": card_id,
            "card_name": card_name,
            "card_company": card_company,
            "card_url": url
        }

    except Exception as e:

        print(
            f"카드 상세 수집 실패 "
            f"{card_id}: {e}"
        )

        return {
            "card_id": card_id,
            "card_name": "",
            "card_company": "",
            "card_url": url
        }


# ============================================================
# 메인 크롤러
# ============================================================

async def main():

    print()
    print("=" * 60)
    print("카드고릴라 전체 카드 크롤링 시작")
    print("=" * 60)
    print()


    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000
            }
        )


        # ----------------------------------------------------
        # 카드 목록 수집
        # ----------------------------------------------------

        card_ids = await collect_card_links(page)


        print()
        print("=" * 60)
        print(f"전체 카드 ID: {len(card_ids)}개")
        print("=" * 60)
        print()


        if not card_ids:

            print("카드를 하나도 찾지 못했습니다.")

            await browser.close()

            return


        # ----------------------------------------------------
        # 상세 정보 수집
        # ----------------------------------------------------

        cards = []

        detail_page = await browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000
            }
        )


        total = len(card_ids)


        for index, card_id in enumerate(
            card_ids,
            start=1
        ):

            print(
                f"[{index}/{total}] "
                f"https://www.card-gorilla.com/card/detail/{card_id}"
            )


            card = await collect_card_detail(
                detail_page,
                card_id
            )


            cards.append(card)


        # ----------------------------------------------------
        # JSON 저장
        # ----------------------------------------------------

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
        print(
            f"cards.json 저장 완료: "
            f"{len(cards)}개"
        )
        print("=" * 60)
        print()


        await detail_page.close()

        await browser.close()


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
