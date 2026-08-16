import json
import time
from pathlib import Path

import requests


API_URL = "https://api.card-gorilla.com:8080/v1/cards"

OUTPUT_FILE = Path("cards.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.card-gorilla.com/",
}

# 처음부터 너무 크게 잡지 않고
# 실제 확인된 10개 단위로 안전하게 수집
PER_PAGE = 10

# API 요청 사이 잠깐 대기
REQUEST_DELAY = 0.2


def get_cards(page):
    """
    카드고릴라 API에서 한 페이지의 카드를 가져온다.
    """

    params = {
        "p": page,
        "perPage": PER_PAGE,
        "is_discon": 0,
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=HEADERS,
        timeout=30,
    )

    print(
        f"[API] p={page} "
        f"status={response.status_code}"
    )

    response.raise_for_status()

    result = response.json()

    # API 응답 구조 확인
    if not isinstance(result, dict):
        raise RuntimeError(
            "API 응답이 JSON 객체가 아닙니다."
        )

    if "data" not in result:
        raise RuntimeError(
            f"API 응답에 data가 없습니다: "
            f"{list(result.keys())}"
        )

    return result


def crawl_all_cards():
    """
    카드고릴라 전체 카드 수집
    """

    print()
    print("=" * 70)
    print("카드고릴라 전체 카드 API 크롤링 시작")
    print("=" * 70)

    all_cards = []

    # --------------------------------------------------
    # 첫 페이지
    # 전체 카드 수 확인
    # --------------------------------------------------

    first_result = get_cards(1)

    total = first_result.get("total", 0)

    first_cards = first_result.get(
        "data",
        []
    )

    print()
    print(f"전체 카드 수: {total}")
    print(
        f"1페이지 카드 수: "
        f"{len(first_cards)}"
    )

    if total == 0:
        print("카드가 없습니다.")
        return []

    all_cards.extend(
        first_cards
    )

    # --------------------------------------------------
    # 전체 페이지 수 계산
    # --------------------------------------------------

    total_pages = (
        total + PER_PAGE - 1
    ) // PER_PAGE

    print(
        f"전체 페이지 수: "
        f"{total_pages}"
    )

    # --------------------------------------------------
    # 2페이지부터 수집
    # --------------------------------------------------

    for page in range(
        2,
        total_pages + 1
    ):

        try:

            result = get_cards(
                page
            )

            cards = result.get(
                "data",
                []
            )

            if not cards:
                print(
                    f"[{page}] 카드가 없어 "
                    f"수집을 종료합니다."
                )
                break

            all_cards.extend(
                cards
            )

            print(
                f"[{page}/{total_pages}] "
                f"{len(cards)}개 수집 "
                f"/ 누적 {len(all_cards)}개"
            )

            time.sleep(
                REQUEST_DELAY
            )

        except Exception as e:

            print()
            print(
                f"[ERROR] "
                f"{page}페이지 수집 실패"
            )

            print(e)

            raise

    # --------------------------------------------------
    # idx 기준 중복 제거
    # --------------------------------------------------

    unique_cards = {}

    for card in all_cards:

        if not isinstance(
            card,
            dict
        ):
            continue

        card_idx = card.get(
            "idx"
        )

        if card_idx is not None:

            unique_cards[
                str(card_idx)
            ] = card

    cards = list(
        unique_cards.values()
    )

    print()
    print("=" * 70)
    print("수집 완료")
    print("=" * 70)

    print(
        f"API 수집 카드: "
        f"{len(all_cards)}개"
    )

    print(
        f"중복 제거 후: "
        f"{len(cards)}개"
    )

    print(
        f"API total: "
        f"{total}개"
    )

    return cards


def save_cards(cards):

    with open(
        OUTPUT_FILE,
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
        f"{OUTPUT_FILE} 저장 완료"
    )


def main():

    cards = crawl_all_cards()

    if not cards:

        print(
            "저장할 카드가 없습니다."
        )

        return

    save_cards(
        cards
    )

    print()
    print("=" * 70)
    print("최종 결과")
    print("=" * 70)

    print(
        f"cards.json: "
        f"{len(cards)}개"
    )


if __name__ == "__main__":
    main()
