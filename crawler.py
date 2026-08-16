import json
import time
from pathlib import Path

import requests


# ============================================================
# 설정
# ============================================================

API_URL = "https://api.card-gorilla.com:8080/v1/cards"

OUTPUT_FILE = Path("cards.json")

# 실제 확인된 API 파라미터
PER_PAGE = 10

# API 요청 사이 대기 시간
REQUEST_DELAY = 0.5

# 서버 오류 발생 시 최대 재시도 횟수
MAX_RETRIES = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.card-gorilla.com/",
}


# ============================================================
# API 요청
# ============================================================

def get_cards(page):
    """
    카드고릴라 API에서 특정 페이지의 카드를 가져온다.

    500 오류나 네트워크 오류가 발생하면
    최대 MAX_RETRIES번 재시도한다.
    """

    params = {
        "p": page,
        "perPage": PER_PAGE,
        "is_discon": 0,
    }

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = requests.get(
                API_URL,
                params=params,
                headers=HEADERS,
                timeout=30,
            )

            print(
                f"[API] p={page} "
                f"status={response.status_code} "
                f"(시도 {attempt}/{MAX_RETRIES})"
            )

            # ------------------------------------------------
            # 정상 응답
            # ------------------------------------------------

            if response.status_code == 200:

                result = response.json()

                if not isinstance(result, dict):
                    raise RuntimeError(
                        "API 응답 형식이 올바르지 않습니다."
                    )

                if "data" not in result:
                    raise RuntimeError(
                        "API 응답에 data가 없습니다."
                    )

                return result

            # ------------------------------------------------
            # 서버 오류 500번대
            # ------------------------------------------------

            if response.status_code >= 500:

                if attempt < MAX_RETRIES:

                    wait_seconds = attempt * 3

                    print(
                        f"[RETRY] "
                        f"{page}페이지 서버 오류 "
                        f"{response.status_code}"
                    )

                    print(
                        f"       {wait_seconds}초 후 재시도합니다."
                    )

                    time.sleep(wait_seconds)

                    continue

                print(
                    f"[ERROR] "
                    f"{page}페이지 "
                    f"{MAX_RETRIES}회 재시도 실패"
                )

                response.raise_for_status()

            # ------------------------------------------------
            # 400 등 기타 HTTP 오류
            # ------------------------------------------------

            response.raise_for_status()

        except requests.exceptions.RequestException as e:

            if attempt < MAX_RETRIES:

                wait_seconds = attempt * 3

                print(
                    f"[RETRY] "
                    f"{page}페이지 요청 오류"
                )

                print(
                    f"       {e}"
                )

                print(
                    f"       {wait_seconds}초 후 재시도합니다."
                )

                time.sleep(wait_seconds)

                continue

            print(
                f"[ERROR] "
                f"{page}페이지 요청 실패"
            )

            raise

    raise RuntimeError(
        f"{page}페이지 API 요청에 실패했습니다."
    )


# ============================================================
# 전체 카드 크롤링
# ============================================================

def crawl_all_cards():

    print()
    print("=" * 70)
    print("카드고릴라 전체 카드 API 크롤링 시작")
    print("=" * 70)

    all_cards = []

    # --------------------------------------------------------
    # 첫 번째 요청
    # 전체 카드 수 확인
    # --------------------------------------------------------

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

        print(
            "카드가 없습니다."
        )

        return []

    all_cards.extend(
        first_cards
    )

    # --------------------------------------------------------
    # 전체 페이지 수 계산
    # --------------------------------------------------------

    total_pages = (
        total + PER_PAGE - 1
    ) // PER_PAGE

    print(
        f"전체 페이지 수: "
        f"{total_pages}"
    )

    # --------------------------------------------------------
    # 나머지 페이지 수집
    # --------------------------------------------------------

    for page in range(
        2,
        total_pages + 1
    ):

        result = get_cards(page)

        cards = result.get(
            "data",
            []
        )

        if not cards:

            print()
            print(
                f"[WARNING] "
                f"{page}페이지에서 카드가 없습니다."
            )

            print(
                "수집을 중단합니다."
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

        # API에 너무 빠르게 요청하지 않도록 대기
        time.sleep(
            REQUEST_DELAY
        )

    # --------------------------------------------------------
    # 중복 제거
    # --------------------------------------------------------

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

        if card_idx is None:
            continue

        unique_cards[
            str(card_idx)
        ] = card

    cards = list(
        unique_cards.values()
    )

    # --------------------------------------------------------
    # 결과 출력
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 카드 수 검증
    # --------------------------------------------------------

    if len(cards) != total:

        print()
        print(
            "⚠️ 주의: API total과 실제 수집 카드 수가 다릅니다."
        )

        print(
            f"API total = {total}"
        )

        print(
            f"실제 수집 = {len(cards)}"
        )

    else:

        print()
        print(
            "✅ 전체 카드가 정상적으로 수집되었습니다."
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

        print()
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
        f"cards.json 카드 수: "
        f"{len(cards)}개"
    )

    print(
        f"저장 위치: "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    main()
