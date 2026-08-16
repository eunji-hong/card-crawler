import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright


LIST_URL = "https://www.card-gorilla.com/search/card?cate=CRD"
BASE_URL = "https://www.card-gorilla.com"


def get_card_ids(page):

    card_ids = set()

    links = page.locator(
        'a[href*="/card/detail/"]'
    ).all()

    for link in links:
        try:
            href = link.get_attribute("href")

            if not href:
                continue

            match = re.search(
                r"/card/detail/(\d+)",
                href
            )

            if match:
                card_ids.add(match.group(1))

        except Exception:
            pass

    return card_ids


def crawl_card_list(page):

    print("카드 목록 페이지 접속")

    page.goto(
        LIST_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(3000)

    print("페이지 로딩 완료")

    # 처음 카드 ID 수집
    card_ids = get_card_ids(page)

    print(
        f"현재 발견 카드: {len(card_ids)}개"
    )


    # ==========================================
    # 카드 더보기 반복 클릭
    # ==========================================

    previous_count = 0
    same_count = 0

    while True:

        # 현재 카드 수
        card_ids = get_card_ids(page)

        current_count = len(card_ids)

        print(
            f"현재 발견 카드: {current_count}개"
        )


        # ------------------------------------------
        # 카드 수가 증가하지 않았는지 확인
        # ------------------------------------------

        if current_count == previous_count:
            same_count += 1
        else:
            same_count = 0

        previous_count = current_count


        # ------------------------------------------
        # 카드 더보기 버튼 찾기
        # ------------------------------------------

        more_button = None

        buttons = page.locator(
            "button"
        ).all()

        for button in buttons:

            try:

                if not button.is_visible():
                    continue

                text = button.inner_text().strip()

                if "카드 더보기" in text:
                    more_button = button
                    break

            except Exception:
                pass


        # ------------------------------------------
        # 버튼을 못 찾으면 종료
        # ------------------------------------------

        if more_button is None:

            print(
                "카드 더보기 버튼을 찾지 못했습니다."
            )

            break


        # ------------------------------------------
        # 버튼이 비활성화됐는지 확인
        # ------------------------------------------

        try:

            if more_button.is_disabled():

                print(
                    "카드 더보기 버튼이 비활성화되었습니다."
                )

                break

        except Exception:
            pass


        # ------------------------------------------
        # 카드 더보기 클릭
        # ------------------------------------------

        print(
            "카드 더보기 클릭"
        )

        try:

            more_button.scroll_into_view_if_needed()

            page.wait_for_timeout(300)

            more_button.click(
                timeout=5000
            )

        except Exception as e:

            print(
                f"버튼 클릭 실패: {e}"
            )

            break


        # ------------------------------------------
        # 카드 추가 로딩 대기
        # ------------------------------------------

        page.wait_for_timeout(1500)


        # ------------------------------------------
        # 새로운 카드가 나타날 때까지 대기
        # ------------------------------------------

        try:

            page.wait_for_function(
                """
                (oldCount) => {
                    return document.querySelectorAll(
                        'a[href*="/card/detail/"]'
                    ).length > oldCount;
                }
                """,
                arg=current_count,
                timeout=5000
            )

        except Exception:

            pass


        # ------------------------------------------
        # 혹시 로딩 중이면 조금 더 기다림
        # ------------------------------------------

        page.wait_for_timeout(500)


        # ------------------------------------------
        # 안전장치
        # ------------------------------------------

        new_count = len(
            get_card_ids(page)
        )

        if new_count == current_count:

            same_count += 1

        else:

            same_count = 0


        # 3번 연속 카드 증가가 없으면 종료
        if same_count >= 3:

            print(
                "새로운 카드가 더 이상 발견되지 않아 종료"
            )

            break


    return get_card_ids(page)


def crawl_card_detail(page, card_id):

    card_url = (
        f"{BASE_URL}/card/detail/{card_id}"
    )

    try:

        page.goto(
            card_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(500)


        # ==========================================
        # 카드명
        # ==========================================

        card_name = ""

        h1 = page.locator("h1")

        if h1.count() > 0:

            card_name = (
                h1.first.inner_text()
                .strip()
            )


        if not card_name:

            card_name = page.title()

            card_name = re.sub(
                r"\s*\|\s*카드고릴라.*$",
                "",
                card_name
            ).strip()


        if not card_name:

            return None


        # ==========================================
        # 카드사
        # ==========================================

        body_text = page.locator(
            "body"
        ).inner_text()

        company = ""


        # 카드명 · 카드사
        pattern = (
            re.escape(card_name)
            + r"\s*·\s*([^\n]+)"
        )

        match = re.search(
            pattern,
            body_text
        )

        if match:

            company = (
                match.group(1)
                .strip()
            )


        # ==========================================
        # 카드사 보완
        # ==========================================

        if not company:

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
                "BC바로카드",
                "케이뱅크",
                "카카오뱅크",
                "토스뱅크",
                "전북은행",
                "광주은행",
                "제주은행",
                "Sh수협은행",
                "iM뱅크",
                "BNK부산은행",
                "BNK경남은행"
            ]

            for company_name in companies:

                if company_name in body_text:

                    company = company_name

                    break


        return {
            "card_id": card_id,
            "card_name": card_name,
            "company": company,
            "card_url": card_url
        }


    except Exception as e:

        print(
            f"카드 {card_id} 수집 실패: {e}"
        )

        return None


def save_cards(cards):

    path = Path(
        "cards.json"
    )

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

    print()
    print(
        f"cards.json 저장 완료: {len(cards)}개"
    )


def main():

    print("=" * 60)
    print("카드고릴라 전체 카드 크롤링 시작")
    print("=" * 60)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 2000
            }
        )


        # ==========================================
        # 1. 전체 카드 ID 수집
        # ==========================================

        card_ids = crawl_card_list(page)

        print()
        print(
            "=" * 50
        )

        print(
            f"전체 카드 ID: {len(card_ids)}개"
        )

        print(
            "=" * 50
        )


        # ==========================================
        # 2. 상세 페이지 수집
        # ==========================================

        cards = []

        sorted_ids = sorted(
            card_ids,
            key=int
        )

        for index, card_id in enumerate(
            sorted_ids,
            start=1
        ):

            print(
                f"[{index}/{len(sorted_ids)}] "
                f"{BASE_URL}/card/detail/{card_id}"
            )

            card = crawl_card_detail(
                page,
                card_id
            )

            if card:

                cards.append(card)

                print(
                    f"  카드명: {card['card_name']}"
                )

                print(
                    f"  카드사: {card['company']}"
                )


        browser.close()


    # ==========================================
    # 3. 중복 제거
    # ==========================================

    unique_cards = {}

    for card in cards:

        unique_cards[
            card["card_id"]
        ] = card


    cards = list(
        unique_cards.values()
    )


    print()
    print(
        f"총 {len(cards)}개 카드 수집 완료"
    )


    save_cards(cards)


if __name__ == "__main__":

    main()
