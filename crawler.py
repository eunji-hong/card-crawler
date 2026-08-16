import json
import time
from playwright.sync_api import sync_playwright

URL = "https://www.card-gorilla.com/card/credit"

print("=" * 50)
print("카드고릴라 전체 카드 크롤링 시작")
print("=" * 50)

cards = {}

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page(
        viewport={"width": 1440, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    )

    print("카드 목록 페이지 접속")

    page.goto(
        URL,
        wait_until="networkidle",
        timeout=60000
    )

    print("페이지 로딩 완료")

    # 처음부터 카드 수집
    def collect_cards():

        links = page.locator(
            'a[href*="/card/detail/"]'
        )

        count = links.count()

        for i in range(count):

            try:
                link = links.nth(i)

                href = link.get_attribute("href")

                if not href:
                    continue

                if "/card/detail/" not in href:
                    continue

                # URL 정리
                if href.startswith("/"):
                    href = "https://www.card-gorilla.com" + href

                # 카드 ID
                card_id = href.rstrip("/").split("/")[-1]

                # 텍스트
                text = link.inner_text().strip()

                if card_id not in cards:

                    cards[card_id] = {
                        "card_id": card_id,
                        "card_name": text,
                        "card_url": href
                    }

        return len(cards)

    # 첫 수집
    before = collect_cards()

    print(f"현재 발견 카드: {before}개")

    # 카드 더보기 반복
    for attempt in range(100):

        buttons = page.get_by_text(
            "카드 더보기",
            exact=True
        )

        count = buttons.count()

        if count == 0:

            print("카드 더보기 버튼을 찾지 못했습니다.")
            break

        button = buttons.last

        try:

            if not button.is_visible():
                break

            print(
                f"카드 더보기 클릭 "
                f"({attempt + 1}/100)"
            )

            before_count = len(cards)

            button.scroll_into_view_if_needed()

            button.click(
                timeout=10000
            )

            # JS 데이터 로딩 대기
            page.wait_for_timeout(1500)

            after_count = collect_cards()

            print(
                f"현재 발견 카드: "
                f"{after_count}개"
            )

            # 더 이상 증가하지 않으면 종료
            if after_count == before_count:

                print(
                    "새로운 카드가 추가되지 않아 "
                    "종료합니다."
                )

                break

        except Exception as e:

            print(
                "더보기 클릭 오류:",
                e
            )

            break

    # 마지막 수집
    total = collect_cards()

    print("=" * 50)
    print(f"전체 카드 ID: {total}개")
    print("=" * 50)

    browser.close()


# JSON 저장
result = list(cards.values())

with open(
    "cards.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )

print(
    f"cards.json 저장 완료: "
    f"{len(result)}개"
)

print("=" * 50)
print("크롤링 완료")
print("=" * 50)
