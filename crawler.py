import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "https://m.card-gorilla.com"
LIST_URL = "https://m.card-gorilla.com/card/credit/12"


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
            LIST_URL,
            wait_until="networkidle",
            timeout=60000
        )

        print("페이지 로딩 완료")


        # ==================================================
        # 1. 카드 상세 URL을 계속 수집
        # ==================================================

        card_ids = set()

        no_change_count = 0

        previous_count = 0

        while True:

            # 현재 페이지에 존재하는 카드 링크 수집
            links = page.locator(
                'a[href*="/card/detail/"]'
            ).all()

            for link in links:

                try:

                    href = link.get_attribute(
                        "href"
                    )

                    if not href:
                        continue

                    match = re.search(
                        r"/card/detail/(\d+)",
                        href
                    )

                    if match:

                        card_ids.add(
                            match.group(1)
                        )

                except Exception:
                    continue


            current_count = len(card_ids)

            print(
                f"현재 발견 카드: {current_count}개"
            )


            # ==================================================
            # 카드가 새로 발견됐는지 확인
            # ==================================================

            if current_count == previous_count:

                no_change_count += 1

            else:

                no_change_count = 0

                previous_count = current_count


            # ==================================================
            # 더보기 버튼 찾기
            # ==================================================

            clicked = False

            buttons = page.locator(
                "button"
            ).all()

            for button in buttons:

                try:

                    if not button.is_visible():
                        continue

                    text = button.inner_text().strip()

                    if text in [
                        "더보기",
                        "더 보기",
                        "다음",
                        "다음 페이지",
                        "카드 더보기"
                    ]:

                        print(
                            f"'{text}' 버튼 클릭"
                        )

                        button.click(
                            timeout=3000
                        )

                        page.wait_for_timeout(
                            1500
                        )

                        clicked = True

                        break

                except Exception:
                    continue


            if clicked:

                continue


            # ==================================================
            # 더보기 버튼이 없으면 스크롤
            # ==================================================

            old_height = page.evaluate(
                "document.body.scrollHeight"
            )

            page.evaluate(
                """
                window.scrollTo(
                    0,
                    document.body.scrollHeight
                )
                """
            )

            page.wait_for_timeout(
                1500
            )

            new_height = page.evaluate(
                "document.body.scrollHeight"
            )


            # ==================================================
            # 더 이상 변화가 없으면 종료
            # ==================================================

            if (
                new_height == old_height
                and no_change_count >= 3
            ):

                print(
                    "새로운 카드가 더 이상 발견되지 않아 종료"
                )

                break


        print()
        print(
            f"전체 카드 ID: {len(card_ids)}개"
        )


        # ==================================================
        # 2. 카드 상세 페이지에서 정보 수집
        # ==================================================

        for index, card_id in enumerate(
            sorted(card_ids, key=int),
            start=1
        ):

            card_url = (
                f"{BASE_URL}/card/detail/{card_id}"
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

                page.wait_for_timeout(300)


                # ------------------------------------------
                # 카드명 + 카드사
                # ------------------------------------------

                title_text = ""

                # h1 우선
                h1 = page.locator("h1")

                if h1.count() > 0:

                    title_text = (
                        h1.first.inner_text()
                        .strip()
                    )


                # h1이 없으면 페이지 title
                if not title_text:

                    title_text = page.title()

                    title_text = re.sub(
                        r"\s*\|\s*카드고릴라.*$",
                        "",
                        title_text
                    ).strip()


                if not title_text:
                    continue


                # 상세 페이지 본문
                body_text = page.locator(
                    "body"
                ).inner_text()


                body_text = re.sub(
                    r"\s+",
                    " ",
                    body_text
                )


                # ------------------------------------------
                # 카드사 추출
                #
                # 예:
                # 신한카드 Mr.Life · 신한카드
                # ------------------------------------------

                company = ""

                pattern = (
                    re.escape(title_text)
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


                # ------------------------------------------
                # 카드사 보완
                # ------------------------------------------

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
                        "BC 바로카드",
                        "BC바로카드",
                        "케이뱅크",
                        "카카오뱅크",
                        "토스뱅크",
                        "전북은행",
                        "광주은행",
                        "제주은행",
                        "Sh수협은행",
                        "우체국",
                        "SC제일은행",
                        "BNK부산은행",
                        "BNK경남은행",
                        "DGB대구은행",
                        "iM뱅크"
                    ]

                    for company_name in companies:

                        if company_name in body_text:

                            company = company_name

                            break


                cards.append({
                    "card_id": card_id,
                    "card_name": title_text,
                    "company": company,
                    "card_url": card_url
                })


            except Exception as e:

                print(
                    f"카드 {card_id} 실패: {e}"
                )


        browser.close()


    # ==================================================
    # 3. 중복 제거
    # ==================================================

    unique_cards = {}

    for card in cards:

        unique_cards[
            card["card_id"]
        ] = card


    return list(
        unique_cards.values()
    )


def save_cards(cards):

    path = Path(
        "cards.json"
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            cards,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        f"cards.json 저장 완료: {len(cards)}개"
    )


if __name__ == "__main__":

    print("=" * 60)
    print("카드고릴라 전체 카드 크롤링 시작")
    print("=" * 60)

    cards = crawl_cards()

    print()
    print(
        f"총 {len(cards)}개 카드 수집 완료"
    )

    save_cards(cards)
