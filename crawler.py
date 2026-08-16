import json
import time
from pathlib import Path

import requests


# ============================================================
# 설정
# ============================================================

API_URL = "https://api.card-gorilla.com:8080/v1/cards"

OUTPUT_FILE = Path("cards.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.card-gorilla.com/",
}

# 한 번에 요청할 카드 수
# 가장 큰 값부터 시도한다.
PAGE_SIZES = [
    1450,
    1000,
    500,
    300,
    200,
    100,
    50,
    30,
    20,
    10,
]

TIMEOUT = 60


# ============================================================
# API 요청
# ============================================================

def request_cards(page, per_page):
    """
    카드고릴라 API 요청
    """

    params = {
        "p": page,
        "perPage": per_page,
        "is_discon": 0,
    }

    print()
    print("-" * 60)
    print(
        f"API 요청: p={page}, perPage={per_page}"
    )

    response = requests.get(
        API_URL,
        params=params,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    print(
        f"STATUS: {response.status_code}"
    )

    if response.status_code != 200:
        print(
            "응답:",
            response.text[:500]
        )
        return None

    try:
        result = response.json()
    except Exception as e:
        print(
            "JSON 변환 실패:",
            e
        )
        return None

    return result


# ============================================================
# 한 번에 전체 카드 가져오기
# ============================================================

def crawl_all_cards():

    print()
    print("=" * 70)
    print("카드고릴라 전체 카드 API 크롤링 시작")
    print("=" * 70)

    # --------------------------------------------------------
    # 먼저 전체 카드 수 확인
    # --------------------------------------------------------

    summary = requests.get(
        API_URL,
        params={
            "summaryOnly": "true"
        },
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    print()
    print(
        f"전체 카드 수 API STATUS: "
        f"{summary.status_code}"
    )

    if summary.status_code != 200:

        print(
            "전체 카드 수 확인 실패"
        )

        print(
            summary.text[:500]
        )

        raise RuntimeError(
            "카드고릴라 API 접속 실패"
        )

    summary_data = summary.json()

    total = summary_data.get(
        "total",
        0
    )

    print(
        f"카드고릴라 전체 카드 수: "
        f"{total}"
    )

    if total <= 0:

        print(
            "가져올 카드가 없습니다."
        )

        return []

    # --------------------------------------------------------
    # 가장 큰 perPage부터 시도
    # --------------------------------------------------------

    cards = None
    selected_page_size = None

    for page_size in PAGE_SIZES:

        print()
        print(
            f"perPage={page_size} 테스트"
        )

        result = request_cards(
            page=1,
            per_page=page_size
        )

        if result is None:

            print(
                f"perPage={page_size} "
                f"사용 불가"
            )

            continue

        data = result.get(
            "data",
            []
        )

        actual_count = len(data)

        print(
            f"요청 결과: "
            f"{actual_count}개"
        )

        # ----------------------------------------------------
        # 전체 카드가 한 번에 들어온 경우
        # ----------------------------------------------------

        if actual_count >= total:

            cards = data

            selected_page_size = page_size

            print()
            print(
                "✅ 전체 카드가 한 번에 수집되었습니다."
            )

            break

        # ----------------------------------------------------
        # 일부만 가져온 경우
        # ----------------------------------------------------

        if actual_count > 0:

            cards = data

            selected_page_size = page_size

            print(
                f"perPage={page_size}는 "
                f"{actual_count}개까지 가져왔습니다."
            )

            break

    # --------------------------------------------------------
    # 어떤 방식도 성공하지 못한 경우
    # --------------------------------------------------------

    if cards is None:

        raise RuntimeError(
            "카드 목록 API에서 데이터를 가져오지 못했습니다."
        )

    # --------------------------------------------------------
    # 한 번에 전체가 안 들어왔다면
    # 선택된 perPage로 나머지 페이지 수집
    # --------------------------------------------------------

    if len(cards) < total:

        print()
        print("=" * 70)
        print(
            "한 번에 전체 카드가 들어오지 않았습니다."
        )

        print(
            f"선택된 perPage: "
            f"{selected_page_size}"
        )

        print(
            f"현재 수집: "
            f"{len(cards)}개"
        )

        print(
            f"전체 필요: "
            f"{total}개"
        )

        print("=" * 70)

        # 필요한 페이지 수
        total_pages = (
            total
            + selected_page_size
            - 1
        ) // selected_page_size

        print(
            f"총 {total_pages}페이지 필요"
        )

        # 2페이지부터 요청
        for page in range(
            2,
            total_pages + 1
        ):

            result = request_cards(
                page=page,
                per_page=selected_page_size
            )

            if result is None:

                raise RuntimeError(
                    f"{page}페이지 "
                    "수집 실패"
                )

            page_cards = result.get(
                "data",
                []
            )

            if not page_cards:

                print(
                    f"{page}페이지에 "
                    "카드가 없습니다."
                )

                break

            cards.extend(
                page_cards
            )

            print(
                f"[{page}/{total_pages}] "
                f"{len(page_cards)}개 수집 "
                f"/ 누적 {len(cards)}개"
            )

            time.sleep(0.5)

    # --------------------------------------------------------
    # 중복 제거
    # --------------------------------------------------------

    unique_cards = {}

    for card in cards:

        if not isinstance(
            card,
            dict
        ):
            continue

        card_idx = card.get(
            "idx"
        )

        if card_idx is None:
            continue

        unique_cards[
            str(card_idx)
        ] = card

    cards = list(
        unique_cards.values()
    )

    # --------------------------------------------------------
    # 결과
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("최종 수집 결과")
    print("=" * 70)

    print(
        f"API 전체 카드 수: "
        f"{total}"
    )

    print(
        f"수집한 카드 수: "
        f"{len(cards)}"
    )

    if len(cards) == total:

        print(
            "✅ 1450개 전체 카드 수집 성공"
        )

    else:

        print(
            "⚠️ 카드 수가 일치하지 않습니다."
        )

    return cards


# ============================================================
# JSON 저장
# ============================================================

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
        f"cards.json 저장 완료: "
        f"{len(cards)}개"
    )


# ============================================================
# 메인
# ============================================================

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
    print("크롤링 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
