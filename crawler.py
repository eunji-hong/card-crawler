import requests
from bs4 import BeautifulSoup
import json
import re
import time
from pathlib import Path


BASE_URL = "https://m.card-gorilla.com"

# 카드 목록 페이지
LIST_URL = "https://m.card-gorilla.com/card/credit/12"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


session = requests.Session()
session.headers.update(HEADERS)


def get_soup(url):
    """웹페이지 가져오기"""

    response = session.get(
        url,
        timeout=20
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


def get_card_ids():
    """카드 목록에서 카드 상세 페이지 ID 수집"""

    print("카드 목록 페이지 접속")

    soup = get_soup(LIST_URL)

    card_ids = set()

    # 모든 링크 검사
    for link in soup.find_all("a", href=True):

        href = link["href"]

        # /card/detail/숫자 형태만 찾는다
        match = re.search(
            r"/card/detail/(\d+)",
            href
        )

        if match:
            card_id = match.group(1)
            card_ids.add(card_id)

    print(f"발견한 카드 ID: {len(card_ids)}개")

    return sorted(
        card_ids,
        key=int
    )


def get_card_info(card_id):
    """카드 상세 페이지에서 카드명/카드사 추출"""

    url = f"{BASE_URL}/card/detail/{card_id}"

    try:

        soup = get_soup(url)

        # 페이지 전체 텍스트
        text = soup.get_text(
            " ",
            strip=True
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        # --------------------------------------------------
        # 카드명
        # --------------------------------------------------

        card_name = None

        # 모바일 카드고릴라 상세 페이지의 첫 번째 h1
        h1 = soup.find("h1")

        if h1:
            card_name = h1.get_text(
                " ",
                strip=True
            )

        # h1이 없으면 title 사용
        if not card_name:

            title = soup.find("title")

            if title:

                card_name = title.get_text(
                    " ",
                    strip=True
                )

                card_name = re.sub(
                    r"\s*\|\s*카드고릴라.*$",
                    "",
                    card_name
                ).strip()

        if not card_name:
            return None


        # --------------------------------------------------
        # 카드사
        # --------------------------------------------------

        company = None

        # 카드 상세 페이지 상단의
        #
        # 카드명 · 카드사
        #
        # 형태를 찾는다.

        # 대표적인 카드사 목록
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
            "케이뱅크",
            "카카오뱅크",
            "토스뱅크",
            "전북은행",
            "광주은행",
            "제주은행",
            "수협은행",
            "우체국",
            "iM뱅크",
        ]

        # 카드명 근처에서 카드사 찾기
        for name in companies:

            if name in text:

                company = name
                break

        if not company:
            company = "기타"


        return {
            "card_id": card_id,
            "card_name": card_name,
            "company": company,
            "card_url": url
        }

    except Exception as e:

        print(
            f"[ERROR] 카드 {card_id}: {e}"
        )

        return None


def crawl_cards():

    # 1. 목록에서 카드 ID 수집
    card_ids = get_card_ids()

    cards = []

    # 2. 각각의 카드 상세 페이지 방문
    for index, card_id in enumerate(
        card_ids,
        start=1
    ):

        print(
            f"[{index}/{len(card_ids)}] "
            f"카드 {card_id} 수집 중..."
        )

        card = get_card_info(
            card_id
        )

        if card:

            cards.append(card)

        # 서버에 너무 빠르게 요청하지 않도록
        time.sleep(0.3)


    # 카드 ID 중복 제거
    unique_cards = {}

    for card in cards:

        unique_cards[
            card["card_id"]
        ] = card


    return list(
        unique_cards.values()
    )


def save_cards(cards):

    file_path = Path(
        "cards.json"
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            cards,
            file,
            ensure_ascii=False,
            indent=2
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

    print(
        "cards.json 저장 완료"
    )
