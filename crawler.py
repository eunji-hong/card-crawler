import json
from playwright.sync_api import sync_playwright

URL = "https://www.card-gorilla.com/card/credit"

print("=" * 50)
print("카드고릴라 전체 카드 크롤링 시작")
print("=" * 50)

cards = {}


def collect_cards(page):
    """현재 페이지에 로딩된 카드들을 수집"""

    links = page.locator('a[href*="/card/detail/"]')
    count = links.count()

    for i in range(count):
        try:
            link = links.nth(i)

            href = link.get_attribute("href")

            if not href:
                continue

            if "/card/detail/" not in href:
                continue

            # 상대경로 → 절대경로
            if href.startswith("/"):
                href = "https://www.card-gorilla.com" + href

            # 카드 ID 추출
            card_id = href.rstrip("/").split("/")[-1]

            # 링크 안의 텍스트
            text = link.inner_text().strip()

            # 중복 제거
            if card_id not in cards:
                cards[card_id] = {
                    "card_id": card_id,
                    "card_name": text,
                    "card_url": href
                }

        except Exception as e:
            print(f"카드 수집 오류: {e}")

    return len(cards)


with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page(
        viewport={
            "width": 1440,
            "height": 900
        },
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    )

    print("카드 목록 페이지 접속")

    page.goto(
        URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    # 페이지가 완전히 표시될 때까지 잠시 대기
    page.wait_for_timeout(3000)

    print("페이지 로딩 완료")

    # -------------------------
    # 처음 카드 수집
    # -------------------------

    current = collect_cards(page)

    print(f"현재 발견 카드: {current}개")

    # -------------------------
    # 카드 더보기 반복
    # -------------------------

    for attempt in range(100):

        before = len(cards)

        # 카드 더보기 버튼 찾기
        button = page.get_by_text(
            "카드 더보기",
            exact=True
        )

        button_count = button.count()

        if button_count == 0:
            print("카드 더보기 버튼을 찾지 못했습니다.")
            break

        try:
            # 마지막 버튼 사용
            target = button.last

            if not target.is_visible():
                print("카드 더보기 버튼이 보이지 않습니다.")
                break

            print(
                f"카드 더보기 클릭 "
                f"({attempt + 1}/100)"
            )

            # 버튼 위치로 이동
            target.scroll_into_view_if_needed()

            # 클릭
            target.click(
                timeout=10000
            )

            # 카드 추가 로딩 대기
            page.wait_for_timeout(1500)

            # 새 카드 수집
            after = collect_cards(page)

            print(
                f"현재 발견 카드: {after}개"
            )

            # 카드가 더 이상 늘어나지 않으면 종료
            if after == before:
                print(
                    "새로운 카드가 추가되지 않아 종료합니다."
                )
                break

        except Exception as e:

            print(
                f"더보기 클릭 중 오류: {e}"
            )

            break

    # -------------------------
    # 마지막 수집
    # -------------------------

    total = collect_cards(page)

    print("=" * 50)
    print(f"전체 카드 ID: {total}개")
    print("=" * 50)

    browser.close()


# -------------------------
# cards.json 저장
# -------------------------

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
    f"cards.json 저장 완료: {len(result)}개"
)

print("=" * 50)
print("크롤링 완료")
print("=" * 50)
