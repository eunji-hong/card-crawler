import json
import time
import requests


API_URL = "https://api.card-gorilla.com:8080/v1/cards"

PER_PAGE = 10
MAX_RETRY = 3

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

def request_cards(page, per_page):
    """
    카드고릴라 API에서 특정 페이지를 가져온다.
    """

    params = {
        "p": page,
        "perPage": per_page,
        "is_discon": 0,
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
                f"[API] p={page}, perPage={per_page} "
                f"status={response.status_code} "
                f"(시도 {attempt}/{MAX_RETRY})"
            )

            # 정상
            if response.status_code == 200:

                data = response.json()

                cards = data.get("data", [])

                return data

            # 서버 오류
            if response.status_code >= 500:

                print(
                    f"[RETRY] 서버 오류 "
                    f"{response.status_code}"
                )

                if attempt < MAX_RETRY:

                    wait = attempt * 3

                    print(
                        f"       {wait}초 후 재시도합니다."
                    )

                    time.sleep(wait)

                    continue

                return None

            # 그 외 오류
            print(
                f"[ERROR] HTTP {response.status_code}"
            )

            print(response.text[:500])

            return None

        except requests.RequestException as e:

            print(
                f"[ERROR] 요청 오류: {e}"
            )

            if attempt < MAX_RETRY:

                wait = attempt * 3

                print(
                    f"       {wait}초 후 재시도합니다."
                )

                time.sleep(wait)

            else:

                return None

    return None


# ============================================================
# 첫 페이지에서 전체 카드 수 확인
# ============================================================

def get_total_cards():

    print("=" * 70)
    print("카드고릴라 전체 카드 API 크롤링 시작")
    print("=" * 70)

    result = request_cards(1, PER_PAGE)

    if result is None:

        raise RuntimeError(
            "첫 번째 API 요청에 실패했습니다."
        )

    total = result.get("total", 0)

    cards = result.get("data", [])

    print(f"전체 카드 수: {total}")
    print(f"1페이지 카드 수: {len(cards)}")

    return total


# ============================================================
# 실패한 페이지 세분화 수집
# ============================================================

def recover_page(original_page, per_page):

    """
    기본 요청이 500으로 실패했을 때
    해당 페이지의 카드 범위를 더 작은 단위로 쪼개서 가져온다.

    예:

    p=78, perPage=10 실패

    → 5개 단위
    → 2개 단위
    → 1개 단위

    """

    print()
    print("-" * 70)
    print(
        f"[RECOVER] {original_page}페이지 복구 시작"
    )
    print("-" * 70)

    # --------------------------------------------------------
    # 원래 페이지가 담당하는 카드 번호
    #
    # p=78, perPage=10
    #
    # 771 ~ 780
    # --------------------------------------------------------

    start_index = (
        (original_page - 1) * per_page
    )

    end_index = start_index + per_page - 1

    print(
        f"문제 구간: {start_index + 1} ~ {end_index + 1}"
    )

    # --------------------------------------------------------
    # 단계적으로 작은 크기 사용
    # --------------------------------------------------------

    split_sizes = [5, 2, 1]

    recovered = []

    for split_size in split_sizes:

        print()
        print(
            f"[RECOVER] perPage={split_size} "
            f"방식으로 재시도"
        )

        recovered = []

        current = start_index

        success = True

        while current <= end_index:

            remaining = end_index - current + 1

            size = min(
                split_size,
                remaining
            )

            # 절대 인덱스를 page로 변환
            page = (
                current // size
            ) + 1

            # 정확한 시작 위치를 만들기 위해
            # 가능한 페이지를 계산한다.
            #
            # API의 page는 1부터 시작하며
            # offset = (page - 1) * size
            #

            if current % size != 0:

                success = False

                break

            result = request_cards(
                page,
                size
            )

            if result is None:

                print(
                    f"[RECOVER] 실패 "
                    f"page={page}, size={size}"
                )

                success = False

                break

            cards = result.get(
                "data",
                []
            )

            print(
                f"[RECOVER] "
                f"page={page}, "
                f"size={size}, "
                f"{len(cards)}개"
            )

            recovered.extend(cards)

            current += size

            time.sleep(0.5)

        if success:

            print(
                f"[RECOVER] 복구 성공: "
                f"{len(recovered)}개"
            )

            return recovered

    # --------------------------------------------------------
    # 모든 방법 실패
    # --------------------------------------------------------

    print(
        "[RECOVER] 페이지 복구 실패"
    )

    return None


# ============================================================
# 전체 카드 수집
# ============================================================

def crawl_all_cards():

    total = get_total_cards()

    total_pages = (
        total + PER_PAGE - 1
    ) // PER_PAGE

    print(
        f"전체 페이지 수: {total_pages}"
    )

    print("=" * 70)

    all_cards = []

    for page in range(
        1,
        total_pages + 1
    ):

        result = request_cards(
            page,
            PER_PAGE
        )

        # ----------------------------------------------------
        # 정상 수집
        # ----------------------------------------------------

        if result is not None:

            cards = result.get(
                "data",
                []
            )

            all_cards.extend(cards)

            print(
                f"[{page}/{total_pages}] "
                f"{len(cards)}개 수집 / "
                f"누적 {len(all_cards)}개"
            )

        # ----------------------------------------------------
        # 500 오류 발생
        # ----------------------------------------------------

        else:

            print()
            print(
                f"[WARNING] "
                f"{page}페이지 기본 요청 실패"
            )

            recovered = recover_page(
                page,
                PER_PAGE
            )

            if recovered is None:

                print()
                print(
                    "=" * 70
                )

                print(
                    f"[FATAL] "
                    f"{page}페이지를 복구하지 못했습니다."
                )

                print(
                    "크롤링을 중단합니다."
                )

                raise RuntimeError(
                    f"{page}페이지 수집 실패"
                )

            all_cards.extend(
                recovered
            )

            print(
                f"[{page}/{total_pages}] "
                f"복구 {len(recovered)}개 / "
                f"누적 {len(all_cards)}개"
            )

        # API에 너무 빠르게 요청하지 않도록
        time.sleep(0.5)

    # ========================================================
    # 중복 제거
    # ========================================================

    unique_cards = {}

    for card in all_cards:

        card_id = (
            card.get("idx")
            or card.get("cid")
            or card.get("no")
        )

        if card_id is not None:

            unique_cards[str(card_id)] = card

    cards = list(
        unique_cards.values()
    )

    print()
    print("=" * 70)
    print("수집 완료")
    print("=" * 70)

    print(
        f"API 전체 카드 수 : {total}"
    )

    print(
        f"실제 수집 카드 수 : {len(all_cards)}"
    )

    print(
        f"중복 제거 후 카드 수 : {len(cards)}"
    )

    # --------------------------------------------------------
    # 카드 수 검증
    # --------------------------------------------------------

    if len(cards) < total:

        print()
        print(
            "WARNING:"
        )

        print(
            f"전체 {total}개 중 "
            f"{len(cards)}개만 확보했습니다."
        )

    else:

        print()
        print(
            "SUCCESS:"
        )

        print(
            f"전체 {total}개 카드 수집 완료!"
        )

    return cards


# ============================================================
# JSON 저장
# ============================================================

def save_cards(cards):

    output_file = "cards.json"

    data = {
        "source": "card-gorilla",
        "total": len(cards),
        "cards": cards
    }

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 70)

    print(
        f"{output_file} 저장 완료"
    )

    print(
        f"카드 수: {len(cards)}"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        cards = crawl_all_cards()

        save_cards(cards)

    except Exception as e:

        print()
        print("=" * 70)

        print(
            "크롤링 실패"
        )

        print(
            str(e)
        )

        print("=" * 70)

        raise


if __name__ == "__main__":

    main()
