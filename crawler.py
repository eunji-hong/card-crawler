import json
import time
import re
import requests


# ============================================================
# 기본 설정
# ============================================================

API_URL = "https://api.card-gorilla.com:8080/v1/cards"

# 한 페이지에 100개
PER_PAGE = 100

# 페이지 하나당 최대 재시도
MAX_RETRY = 3

# API 요청 간격
REQUEST_DELAY = 0.5

# 요청 timeout
TIMEOUT = 30


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
# 숫자 변환
# ============================================================

def to_number(value):
    """
    문자열에서 숫자를 안전하게 추출한다.

    예:
    "10%"       -> 10
    "200원/L"   -> 200
    "40원/L"    -> 40
    "월 1만원"  -> 10000
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # 쉼표 제거
    text = text.replace(",", "")

    # 만원
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*만원",
        text
    )

    if match:
        number = float(match.group(1))
        return int(number * 10000)

    # 일반 숫자
    match = re.search(
        r"(\d+(?:\.\d+)?)",
        text
    )

    if not match:
        return None

    number = float(match.group(1))

    if number.is_integer():
        return int(number)

    return number


# ============================================================
# 주유 혜택 추출
# ============================================================

def extract_oil_benefit(card):
    """
    카드 API 응답의 top_benefit에서
    현재 카드 자신의 '주유' 혜택만 추출한다.

    중요:
    event HTML을 분석하지 않는다.

    이유:
    이벤트 HTML에는 다른 카드의 혜택이 함께 들어갈 수 있다.

    예:
    Mr.Life 이벤트 안에
    Deep Oil 10% 할인
    같은 다른 카드 정보가 들어갈 수 있음.

    따라서 top_benefit에서
    title == '주유'
    인 데이터만 사용한다.
    """

    top_benefits = card.get("top_benefit")

    if not isinstance(top_benefits, list):
        return {
            "has_benefit": False,
            "description": None,
            "discount_type": None,
            "discount_value": None
        }

    oil_benefits = []

    # --------------------------------------------------------
    # title == 주유 인 혜택만 추출
    # --------------------------------------------------------

    for benefit in top_benefits:

        if not isinstance(benefit, dict):
            continue

        title = str(
            benefit.get("title", "")
        ).strip()

        if title != "주유":
            continue

        tags = benefit.get("tags", [])

        if not isinstance(tags, list):
            tags = [tags]

        clean_tags = []

        for tag in tags:

            if tag is None:
                continue

            tag_text = str(tag).strip()

            if tag_text:
                clean_tags.append(tag_text)

        if clean_tags:
            oil_benefits.append(
                " ".join(clean_tags)
            )

    # --------------------------------------------------------
    # 주유 혜택 없음
    # --------------------------------------------------------

    if not oil_benefits:

        return {
            "has_benefit": False,
            "description": None,
            "discount_type": None,
            "discount_value": None
        }

    # --------------------------------------------------------
    # 여러 개가 있으면 합쳐서 저장
    # --------------------------------------------------------

    description = " / ".join(
        oil_benefits
    )

    # ========================================================
    # 할인/적립 유형 분석
    # ========================================================

    # --------------------------------------------------------
    # 1. 퍼센트
    #
    # 예:
    # 10% 할인
    # 5% 적립
    # --------------------------------------------------------

    percent_match = re.search(
        r"(\d+(?:\.\d+)?)\s*%",
        description
    )

    if percent_match:

        value = float(
            percent_match.group(1)
        )

        if value.is_integer():
            value = int(value)

        return {
            "has_benefit": True,
            "description": description,
            "discount_type": "percent",
            "discount_value": value
        }

    # --------------------------------------------------------
    # 2. 리터당 금액
    #
    # 예:
    # 200원/L 할인
    # 40원/L 적립
    # --------------------------------------------------------

    per_liter_match = re.search(
        r"(\d+(?:,\d+)?)\s*원\s*/\s*[Ll]",
        description,
        re.IGNORECASE
    )

    if per_liter_match:

        value = int(
            per_liter_match.group(1).replace(",", "")
        )

        return {
            "has_benefit": True,
            "description": description,
            "discount_type": "per_liter",
            "discount_value": value
        }

    # --------------------------------------------------------
    # 3. 리터당 표기 다른 형태
    #
    # 예:
    # 200원/L
    # 200원/ℓ
    # --------------------------------------------------------

    per_liter_match = re.search(
        r"(\d+(?:,\d+)?)\s*원\s*/\s*[ℓ]",
        description
    )

    if per_liter_match:

        value = int(
            per_liter_match.group(1).replace(",", "")
        )

        return {
            "has_benefit": True,
            "description": description,
            "discount_type": "per_liter",
            "discount_value": value
        }

    # --------------------------------------------------------
    # 4. 월 할인 금액
    #
    # 예:
    # 월 1만원 할인
    # 월 최대 2만원
    # --------------------------------------------------------

    monthly_match = re.search(
        r"월\s*(?:최대\s*)?(\d+(?:,\d+)?)\s*만원",
        description
    )

    if monthly_match:

        value = int(
            monthly_match.group(1).replace(",", "")
        ) * 10000

        return {
            "has_benefit": True,
            "description": description,
            "discount_type": "monthly_amount",
            "discount_value": value
        }

    # --------------------------------------------------------
    # 5. 원 단위 할인
    #
    # 예:
    # 5,000원 할인
    # 최대 10,000원 할인
    #
    # 단, 원/L은 위에서 이미 처리됨.
    # --------------------------------------------------------

    amount_match = re.search(
        r"(\d+(?:,\d+)?)\s*원\s*(?:할인|적립)",
        description
    )

    if amount_match:

        value = int(
            amount_match.group(1).replace(",", "")
        )

        return {
            "has_benefit": True,
            "description": description,
            "discount_type": "amount",
            "discount_value": value
        }

    # --------------------------------------------------------
    # 6. 포인트 적립
    #
    # 숫자를 정확히 파악하기 어려운 경우
    # 억지로 숫자를 넣지 않는다.
    # --------------------------------------------------------

    point_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:P|포인트)",
        description,
        re.IGNORECASE
    )

    if point_match:

        value = float(
            point_match.group(1)
        )

        if value.is_integer():
            value = int(value)

        return {
            "has_benefit": True,
            "description": description,
            "discount_type": "point",
            "discount_value": value
        }

    # --------------------------------------------------------
    # 7. 주유 혜택은 있지만 수치 파악 불가
    #
    # 절대로 임의의 숫자를 넣지 않는다.
    # --------------------------------------------------------

    return {
        "has_benefit": True,
        "description": description,
        "discount_type": None,
        "discount_value": None
    }


# ============================================================
# 카드 데이터 정리
# ============================================================

def simplify_card(card):
    """
    API 원본 카드 데이터를
    우리 프로젝트에서 사용할 형태로 변환한다.
    """

    corp = card.get("corp") or {}
    brand = card.get("brand") or {}
    card_img = card.get("card_img") or {}

    # --------------------------------------------------------
    # 카드 ID
    # --------------------------------------------------------

    card_id = card.get("idx")

    # --------------------------------------------------------
    # 카드사
    # --------------------------------------------------------

    card_company = (
        card.get("corp_txt")
        or corp.get("name")
    )

    # --------------------------------------------------------
    # 브랜드
    # --------------------------------------------------------

    card_brand = (
        card.get("brand_txt")
        or brand.get("name")
    )

    # --------------------------------------------------------
    # 카드 종류
    # --------------------------------------------------------

    category = (
        card.get("cate_txt")
        or card.get("cate")
    )

    card_type = (
        card.get("c_type_txt")
        or card.get("c_type")
    )

    # --------------------------------------------------------
    # 이미지
    # --------------------------------------------------------

    card_image = card_img.get("url")

    # --------------------------------------------------------
    # 주유 혜택
    # --------------------------------------------------------

    oil_benefit = extract_oil_benefit(
        card
    )

    # --------------------------------------------------------
    # 최종 데이터
    # --------------------------------------------------------

    return {
        "card_id": card_id,
        "card_name": card.get("name"),
        "card_company": card_company,
        "brand": card_brand,
        "category": category,
        "card_type": card_type,
        "card_image": card_image,
        "oil_benefit": oil_benefit
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

    for attempt in range(
        1,
        MAX_RETRY + 1
    ):

        try:

            response = requests.get(
                API_URL,
                params=params,
                headers=HEADERS,
                timeout=TIMEOUT
            )

            print(
                f"[API] p={page}, "
                f"perPage={PER_PAGE} "
                f"status={response.status_code} "
                f"(시도 {attempt}/{MAX_RETRY})"
            )

            # ------------------------------------------------
            # 성공
            # ------------------------------------------------

            if response.status_code == 200:

                try:

                    return response.json()

                except ValueError as e:

                    print(
                        f"[ERROR] JSON 파싱 실패: {e}"
                    )

                    return None

            # ------------------------------------------------
            # 서버 오류
            # ------------------------------------------------

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

                print(
                    f"[ERROR] p={page} "
                    f"{MAX_RETRY}회 재시도 실패"
                )

                return None

            # ------------------------------------------------
            # 400 등 기타 오류
            # ------------------------------------------------

            print(
                f"[ERROR] HTTP "
                f"{response.status_code}"
            )

            print(
                response.text[:500]
            )

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

                print(
                    f"[ERROR] p={page} "
                    f"요청 실패"
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

    # --------------------------------------------------------
    # 첫 페이지
    # --------------------------------------------------------

    first = get_cards(1)

    if first is None:

        raise RuntimeError(
            "첫 페이지 API 요청 실패"
        )

    total = first.get(
        "total",
        0
    )

    first_cards = first.get(
        "data",
        []
    )

    print(
        f"전체 카드 수: {total}"
    )

    print(
        f"1페이지 카드 수: "
        f"{len(first_cards)}"
    )

    # --------------------------------------------------------
    # 전체 페이지 수
    # --------------------------------------------------------

    total_pages = (
        total + PER_PAGE - 1
    ) // PER_PAGE

    print(
        f"전체 페이지 수: "
        f"{total_pages}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # 전체 카드
    # --------------------------------------------------------

    all_cards = []

    # 첫 페이지 추가
    all_cards.extend(
        first_cards
    )

    # 실패 페이지
    failed_pages = []

    # --------------------------------------------------------
    # 2페이지부터 끝까지
    # --------------------------------------------------------

    for page in range(
        2,
        total_pages + 1
    ):

        result = get_cards(page)

        # ----------------------------------------------------
        # 성공
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 실패
        # ----------------------------------------------------

        else:

            print()
            print(
                "-" * 70
            )

            print(
                f"[WARNING] "
                f"{page}페이지 수집 실패"
            )

            print(
                "해당 페이지는 기록하고 "
                "다음 페이지로 진행합니다."
            )

            print(
                "-" * 70
            )

            failed_pages.append(
                page
            )

        # ----------------------------------------------------
        # API 요청 간격
        # ----------------------------------------------------

        time.sleep(
            REQUEST_DELAY
        )

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

        if card_id is None:
            continue

        unique_cards[
            str(card_id)
        ] = card

    unique_raw_cards = list(
        unique_cards.values()
    )

    # ========================================================
    # 카드 데이터 가공
    # ========================================================

    simplified_cards = []

    for card in unique_raw_cards:

        try:

            simplified = simplify_card(
                card
            )

            simplified_cards.append(
                simplified
            )

        except Exception as e:

            print(
                f"[WARNING] 카드 데이터 "
                f"가공 실패: {e}"
            )

    # ========================================================
    # 결과
    # ========================================================

    print()
    print("=" * 70)
    print("크롤링 종료")
    print("=" * 70)

    print(
        f"API 전체 카드 수 : "
        f"{total}"
    )

    print(
        f"API 수집 카드 수 : "
        f"{len(all_cards)}"
    )

    print(
        f"중복 제거 후 : "
        f"{len(unique_raw_cards)}"
    )

    print(
        f"최종 카드 수 : "
        f"{len(simplified_cards)}"
    )

    print(
        f"실패한 페이지 수 : "
        f"{len(failed_pages)}"
    )

    if failed_pages:

        print(
            f"실패 페이지 : "
            f"{failed_pages}"
        )

    else:

        print(
            "모든 페이지 정상 수집"
        )

    print("=" * 70)

    return {
        "total": total,
        "cards": simplified_cards,
        "failed_pages": failed_pages
    }


# ============================================================
# JSON 저장
# ============================================================

def save_cards(result):

    output = {
        "source": "card-gorilla",

        "total": result["total"],

        "collected": len(
            result["cards"]
        ),

        "failed_page_count": len(
            result["failed_pages"]
        ),

        "failed_pages": result[
            "failed_pages"
        ],

        "cards": result[
            "cards"
        ]
    }

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

    print()
    print("=" * 70)
    print("cards.json 저장 완료")
    print("=" * 70)

    print(
        f"전체 카드 : "
        f"{result['total']}"
    )

    print(
        f"수집 카드 : "
        f"{len(result['cards'])}"
    )

    print(
        f"실패 페이지 : "
        f"{result['failed_pages']}"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("CARD GORILLA CRAWLER")
    print("=" * 70)
    print()

    try:

        result = crawl_all_cards()

        # ----------------------------------------------
        # 성공/부분 성공 관계없이 JSON 저장
        # ----------------------------------------------

        save_cards(result)

        print()
        print("=" * 70)
        print("작업 완료")
        print("=" * 70)

        if result["failed_pages"]:

            print(
                "일부 페이지는 실패했지만 "
                "cards.json 저장까지 완료했습니다."
            )

        else:

            print(
                "전체 카드 정상 수집 및 저장 완료"
            )

        print("=" * 70)

    except Exception as e:

        print()
        print("=" * 70)
        print("[FATAL ERROR]")
        print("=" * 70)

        print(e)

        print("=" * 70)

        raise


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    main()
