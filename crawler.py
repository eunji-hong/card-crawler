import json
import time
import requests


# ============================================================
# 설정
# ============================================================

API_URL = "https://api.card-gorilla.com:8080/v1/cards"

# 한 페이지에 100개씩 요청
PER_PAGE = 100

# 페이지별 최대 재시도 횟수
MAX_RETRY = 3

# API 요청 간 대기 시간
REQUEST_DELAY = 1


HEADERS = {
    "Referer": "https://www.card-gorilla.com/",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


# ============================================================
# API 요청
# ============================================================

def get_cards(page):

    params = {
        "p": page,
        "perPage": PER_PAGE,
        "is_discon": 0
    }

    for attempt in range(1, MAX_RETRY + 1):

        try:

            response = requests.get(
                API_URL,
                params=params,
                headers=HEADERS,
                timeout=30
            )

            print(
                f"[API] p={page}, "
                f"perPage={PER_PAGE} "
                f"status={response.status_code} "
                f"(시도 {attempt}/{MAX_RETRY})"
            )

            # ==================================================
            # 성공
            # ==================================================

            if response.status_code == 200:

                try:

                    data = response.json()

                    return data

                except ValueError:

                    print(
                        f"[ERROR] p={page} "
                        "JSON 응답 파싱 실패"
                    )

                    return None

            # ==================================================
            # 서버 오류 500
            # ==================================================

            if response.status_code >= 500:

                print(
                    f"[RETRY] p={page} "
                    f"서버 오류 {response.status_code}"
                )

                if attempt < MAX_RETRY:

                    wait = attempt * 3

                    print(
                        f"       {wait}초 후 재시도합니다."
                    )

                    time.sleep(wait)

                    continue

                print(
                    f"[FAILED] p={page} "
                    f"{MAX_RETRY}회 재시도 실패"
                )

                return None

            # ==================================================
            # 기타 HTTP 오류
            # ==================================================

            print(
                f"[ERROR] p={page} "
                f"HTTP {response.status_code}"
            )

            print(
                response.text[:500]
            )

            return None

        except requests.RequestException as e:

            print(
                f"[ERROR] p={page} "
                f"요청 오류: {e}"
            )

            if attempt < MAX_RETRY:

                wait = attempt * 3

                print(
                    f"       {wait}초 후 재시도합니다."
                )

                time.sleep(wait)

            else:

                print(
                    f"[FAILED] p={page} "
                    "네트워크 요청 실패"
                )

                return None

    return None


# ============================================================
# 전체 카드 크롤링
# ============================================================

def crawl_all_cards():

    print("=" * 70)
    print("카드고릴라 전체 카드 API 크롤링 시작")
    print("=" * 70)

    print(
        f"페이지당 카드 수: {PER_PAGE}개"
    )

    # ========================================================
    # 첫 페이지
    # ========================================================

    first = get_cards(1)

    if first is None:

        print()
        print("=" * 70)
        print("[FATAL] 첫 페이지 API 요청 실패")
        print("=" * 70)

        return {
            "total": 0,
            "cards": [],
            "failed_pages": [1]
        }

    # ========================================================
    # 전체 카드 수
    # ========================================================

    total = first.get(
        "total",
        0
    )

    first_cards = first.get(
        "data",
        []
    )

    print()
    print(
        f"전체 카드 수: {total}"
    )

    print(
        f"1페이지 카드 수: {len(first_cards)}"
    )

    # ========================================================
    # 전체 페이지 수 계산
    # ========================================================

    total_pages = (
        total + PER_PAGE - 1
    ) // PER_PAGE

    print(
        f"전체 페이지 수: {total_pages}"
    )

    print("=" * 70)

    # ========================================================
    # 카드 저장
    # ========================================================

    all_cards = []

    # 첫 페이지 저장
    all_cards.extend(
        first_cards
    )

    # ========================================================
    # 실패 페이지
    # ========================================================

    failed_pages = []

    # ========================================================
    # 2페이지부터 마지막까지
    # ========================================================

    for page in range(
        2,
        total_pages + 1
    ):

        result = get_cards(page)

        # ====================================================
        # 정상 수집
        # ====================================================

        if result is not None:

            cards = result.get(
                "data",
                []
            )

            all_cards.extend(
                cards
            )

            print(
                f"[{page}/{total_pages}] "
                f"{len(cards)}개 수집 / "
                f"누적 {len(all_cards)}개"
            )

        # ====================================================
        # 실패
        # ====================================================

        else:

            print()
            print("-" * 70)

            print(
                f"[WARNING] "
                f"{page}페이지 수집 실패"
            )

            print(
                "이 페이지는 실패 목록에 기록하고 "
                "다음 페이지로 진행합니다."
            )

            print("-" * 70)

            failed_pages.append(
                page
            )

        # ====================================================
        # API 요청 간격
        # ====================================================

        time.sleep(
            REQUEST_DELAY
        )

    # ========================================================
    # 중복 제거
    # ========================================================

    print()
    print("=" * 70)
    print("중복 카드 제거")
    print("=" * 70)

    unique_cards = {}

    for card in all_cards:

        # ----------------------------------------------------
        # 카드 ID 우선순위
        # ----------------------------------------------------

        card_id = (
            card.get("idx")
            or card.get("cid")
            or card.get("no")
        )

        # ----------------------------------------------------
        # ID가 없는 경우
        # ----------------------------------------------------

        if card_id is None:

            card_id = (
                "unknown_"
                + str(len(unique_cards))
            )

        card_id = str(
            card_id
        )

        # ----------------------------------------------------
        # 중복 제거
        # ----------------------------------------------------

        if card_id not in unique_cards:

            unique_cards[card_id] = card

    cards = list(
        unique_cards.values()
    )

    # ========================================================
    # 수집률
    # ========================================================

    if total > 0:

        collection_rate = (
            len(cards) / total
        ) * 100

    else:

        collection_rate = 0

    # ========================================================
    # 결과 출력
    # ========================================================

    print()
    print("=" * 70)
    print("크롤링 종료")
    print("=" * 70)

    print(
        f"API 전체 카드 수 : {total}"
    )

    print(
        f"수집한 카드 수   : {len(all_cards)}"
    )

    print(
        f"중복 제거 후      : {len(cards)}"
    )

    print(
        f"수집률            : "
        f"{collection_rate:.2f}%"
    )

    print(
        f"실패한 페이지 수 : "
        f"{len(failed_pages)}"
    )

    # ========================================================
    # 실패 페이지 출력
    # ========================================================

    if failed_pages:

        print()

        print(
            f"실패 페이지 : {failed_pages}"
        )

        print()

        print(
            "※ 실패한 페이지의 카드는 "
            "cards.json에 포함되지 않았습니다."
        )

    else:

        print()

        print(
            "모든 페이지 정상 수집"
        )

    print("=" * 70)

    # ========================================================
    # 결과 반환
    # ========================================================

    return {
        "total": total,
        "cards": cards,
        "failed_pages": failed_pages
    }


# ============================================================
# JSON 저장
# ============================================================

def save_cards(result):

    output = {
        "source": "card-gorilla",

        "total": result[
            "total"
        ],

        "collected": len(
            result[
                "cards"
            ]
        ),

        "failed_page_count": len(
            result[
                "failed_pages"
            ]
        ),

        "failed_pages": result[
            "failed_pages"
        ],

        "cards": result[
            "cards"
        ]
    }

    # ========================================================
    # cards.json 저장
    # ========================================================

    with open(
        "cards.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # 저장 결과 출력
    # ========================================================

    print()
    print("=" * 70)
    print("cards.json 저장 완료")
    print("=" * 70)

    print(
        f"전체 카드      : "
        f"{result['total']}"
    )

    print(
        f"수집 카드      : "
        f"{len(result['cards'])}"
    )

    print(
        f"실패 페이지 수 : "
        f"{len(result['failed_pages'])}"
    )

    if result["failed_pages"]:

        print(
            f"실패 페이지    : "
            f"{result['failed_pages']}"
        )

    else:

        print(
            "실패 페이지    : 없음"
        )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        result = crawl_all_cards()

        # ----------------------------------------------------
        # 실패 페이지가 있어도 JSON 저장
        # ----------------------------------------------------

        save_cards(
            result
        )

        print()
        print("=" * 70)
        print("프로그램 정상 종료")
        print("=" * 70)

    except Exception as e:

        # ====================================================
        # 예상하지 못한 오류
        # ====================================================

        print()
        print("=" * 70)
        print("[ERROR] 예상하지 못한 오류 발생")
        print("=" * 70)

        print(e)

        # ----------------------------------------------------
        # 최소한의 cards.json 생성
        # ----------------------------------------------------

        fallback = {
            "source": "card-gorilla",
            "total": 0,
            "collected": 0,
            "failed_page_count": 0,
            "failed_pages": [],
            "cards": [],
            "error": str(e)
        }

        with open(
            "cards.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                fallback,
                f,
                ensure_ascii=False,
                indent=2
            )

        print()
        print(
            "cards.json에 오류 정보를 저장했습니다."
        )

        # ----------------------------------------------------
        # GitHub Actions에서 실패하지 않도록 종료
        # ----------------------------------------------------

        return


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":

    main()
