import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright


URL = "https://m.card-gorilla.com/card/credit/12"


def crawl_cards():

    cards = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 2000
            },
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36"
            )
        )

        print("카드고릴라 접속")

        page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        print("페이지 로딩 완료")

        # 페이지 끝까지 스크롤
        for _ in range(10):

            page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )

            page.wait_for_timeout(1000)

        # 모든 링크 가져오기
        links = page.locator("a").all()

        print(
            f"전체 링크 수: {len(links)}"
        )

        card_ids = set()

        for link in links:

            try:

                href = link.get_attribute("href")

                if not href:
                    continue

                # 카드 상세 페이지 찾기
                match = re.search(
                    r"/card/detail/(\d+)",
                    href
                )

                if match:

                    card_id = match.group(1)

                    card_ids.add(card_id)

            except Exception:
                continue

        print(
            f"발견한 카드 ID: {len(card_ids)}개"
        )

        # 카드 상세 페이지 방문
        for index, card_id in enumerate(
            sorted(card_ids, key=int),
            start=1
        ):

            card_url = (
                f"https://m.card-gorilla.com"
                f"/card/detail/{card_id}"
            )

            print(
                f"[{index}/{len(card_ids)}] "
                f"{card_url}"
            )

            try:

                page.goto(
                    card_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                page.wait_for_timeout(500)

                # 페이지 제목
                title = page.title()

                # 카드명 추출
                card_name = None

                h1 = page.locator("h1")

                if h1.count() > 0:

                    card_name = (
                        h1.first.inner_text()
                        .strip()
                    )

                # h1이 없으면 title 사용
                if not card_name:

                    card_name = title

                # title 정리
                card_name = re.sub(
                    r"\s*\|\s*카드고릴라.*$",
                    "",
                    card_name
                ).strip()

                if not card_name:
                    continue

                cards.append({
                    "card_id": card_id,
                    "card_name": card_name,
                    "card_url": card_url
                })

            except Exception as e:

                print(
                    f"카드 {card_id} 실패: {e}"
                )

        browser.close()

    # 중복 제거
    unique_cards = {}

    for card in cards:

        unique_cards[
            card["card_id"]
        ] = card

    return list(
        unique_cards.values()
    )


def save_cards(cards):

    path = Path("cards.json")

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            cards,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"cards.json 저장 완료: {len(cards)}개"
    )


if __name__ == "__main__":

    print("=" * 50)
    print("카드고릴라 카드 크롤링 시작")
    print("=" * 50)

    cards = crawl_cards()

    print()
    print(
        f"총 {len(cards)}개 카드 수집 완료"
    )

    save_cards(cards)
