import json
import math
import re
import time
import requests


# ============================================================
# 설정
# ============================================================

API_URL = "https://api.card-gorilla.com:8080/v1/cards"

# 한 번에 100개
PER_PAGE = 100

# 페이지 요청 재시도 횟수
MAX_RETRY = 3

# 요청 사이 대기 시간
REQUEST_DELAY = 0.7

# 실패 페이지 재시도 대기
RETRY_DELAY = 3

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

def get_cards(page, per_page=PER_PAGE):
    """
    카드고릴라 카드 API 요청

    실패해도 예외를 발생시키지 않고 None 반환
    """

    params = {
        "p": page,
        "perPage": per_page,
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
                f"perPage={per_page} "
                f"status={response.status_code} "
                f"(시도 {attempt}/{MAX_RETRY})"
            )

            # ------------------------------------------------
            # 정상
            # ------------------------------------------------

            if response.status_code == 200:

                try:
                    return response.json()

                except ValueError:

                    print(
                        f"[ERROR] p={page} "
                        "JSON 파싱 실패"
                    )

                    return None

            # ------------------------------------------------
            # 서버 오류
            # ------------------------------------------------

            if response.status_code >= 500:

                print(
                    f"[RETRY] p={page} "
                    f"서버 오류 {response.status_code}"
                )

                if attempt < MAX_RETRY:

                    wait = RETRY_DELAY * attempt

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
            # 기타 오류
            # ------------------------------------------------

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

                wait = RETRY_DELAY * attempt

                print(
                    f"       {wait}초 후 재시도합니다."
                )

                time.sleep(wait)

            else:

                print(
                    f"[ERROR] p={page} "
                    f"최종 요청 실패"
                )

                return None

    return None


# ============================================================
# HTML 태그 제거
# ============================================================

def clean_html(text):
    """
    HTML 태그를 제거하고 텍스트만 반환
    """

    if not text:
        return ""

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    # HTML entity 일부 처리
    text = (
        text.replace("&nbsp;", " ")
            .replace("&middot;", "·")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&#39;", "'")
            .replace("&quot;", '"')
    )

    # 공백 정리
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n\s+",
        "\n",
        text
    )

    return text.strip()


# ============================================================
# 카드의 모든 혜택 관련 텍스트 추출
# ============================================================

def collect_benefit_text(card):
    """
    API 카드 데이터에서 혜택과 관련된 텍스트를 최대한 모음
    """

    texts = []

    # --------------------------------------------------------
    # search_benefit
    # --------------------------------------------------------

    search_benefit = card.get("search_benefit")

    if isinstance(search_benefit, list):

        for item in search_benefit:

            if isinstance(item, dict):

                for key in [
                    "name",
                    "title",
                    "text",
                    "contents",
                    "content",
                    "benefit"
                ]:

                    value = item.get(key)

                    if value:
                        texts.append(str(value))

            elif item:
                texts.append(str(item))

    # --------------------------------------------------------
    # event
    # --------------------------------------------------------

    event = card.get("event")

    if isinstance(event, dict):

        for key in [
            "card_detail_text",
            "title",
            "subject",
            "detail"
        ]:

            value = event.get(key)

            if value:
                texts.append(clean_html(str(value)))

    # --------------------------------------------------------
    # 기타 카드 필드
    # --------------------------------------------------------

    for key in [
        "benefit",
        "benefits",
        "detail",
        "description",
        "summary"
    ]:

        value = card.get(key)

        if not value:
            continue

        if isinstance(value, str):

            texts.append(
                clean_html(value)
            )

        elif isinstance(value, list):

            for item in value:

                if isinstance(item, dict):

                    for v in item.values():

                        if isinstance(v, str):
                            texts.append(
                                clean_html(v)
                            )

                elif item:

                    texts.append(
                        str(item)
                    )

    return "\n".join(
        text for text in texts if text
    )


# ============================================================
# 주유 관련 문구 찾기
# ============================================================

OIL_KEYWORDS = [
    "주유",
    "주유소",
    "유류",
    "휘발유",
    "경유",
    "자동차 주유",
    "주유 할인",
    "주유 적립",
    "주유 캐시백",
    "주유 포인트",
    "리터당"
]


def find_oil_sentences(text):
    """
    전체 혜택 텍스트에서 주유 관련 문장이 포함된 부분 추출
    """

    if not text:
        return []

    # 줄 단위
    lines = re.split(
        r"[\n\r]+",
        text
    )

    result = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if any(
            keyword in line
            for keyword in OIL_KEYWORDS
        ):

            result.append(line)

    # 줄바꿈으로 안 나뉜 경우를 위해
    # 일정 길이로 분리된 텍스트도 검사
    if not result:

        sentences = re.split(
            r"[.!?]|(?<=다)\s+",
            text
        )

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            if any(
                keyword in sentence
                for keyword in OIL_KEYWORDS
            ):

                result.append(sentence)

    # 중복 제거
    unique = []

    for item in result:

        if item not in unique:
            unique.append(item)

    return unique


# ============================================================
# 주유 할인 타입 분석
# ============================================================

def parse_oil_benefit(sentences):
    """
    주유 혜택 문장에서 할인 형태를 가능한 경우 추출

    정확하게 판단하기 어려운 경우 None
    """

    if not sentences:
        return {
            "has_benefit": False,
            "description": None,
            "discount_type": None,
            "discount_value": None
        }

    description = " ".join(sentences)

    # --------------------------------------------------------
    # 퍼센트 할인
    # 예:
    # 주유 10% 할인
    # 주유소 5% 할인
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
    # 리터당 할인
    # 예:
    # 리터당 100원 할인
    # ℓ당 80원 할인
    # L당 100원 할인
    # --------------------------------------------------------

    liter_match = re.search(
        r"(?:리터|ℓ|L|l)\s*(?:당)?\s*"
        r"(\d[\d,]*)\s*원",
        description,
        flags=re.IGNORECASE
    )

    if liter_match:

        value = int(
            liter_match.group(1)
            .replace(",", "")
        )

        return {
            "has_benefit": True,
            "description": description,
            "discount_type": "won_per_liter",
            "discount_value": value
        }

    # --------------------------------------------------------
    # 단순 원 할인
    # 정확한 단위를 판단하기 어려우므로
    # discount_type은 unknown
    # --------------------------------------------------------

    won_match = re.search(
        r"(\d[\d,]*)\s*원\s*(?:할인|캐시백|적립)",
        description
    )

    if won_match:

        value = int(
            won_match.group(1)
            .replace(",", "")
        )

        return {
            "has_benefit": True,
            "description": description,
            "discount_type": "won",
            "discount_value": value
        }

    # --------------------------------------------------------
    # 주유 혜택은 있지만 할인값을 확실하게 파악 못함
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
    카드고릴라 API 원본 데이터를
    우리 프로젝트에서 사용할 형태로 변환
    """

    card_id = (
        card.get("idx")
        or card.get("cid")
        or card.get("no")
    )

    # --------------------------------------------------------
    # 카드사
    # --------------------------------------------------------

    corp = card.get("corp")

    if isinstance(corp, dict):

        card_company = corp.get(
            "name"
        )

    else:

        card_company = card.get(
            "corp_txt"
        )

    # --------------------------------------------------------
    # 브랜드
    # --------------------------------------------------------

    brand = card.get("brand")

    if isinstance(brand, dict):

        brand_name = brand.get(
            "name"
        )

    else:

        brand_name = card.get(
            "brand_txt"
        )

    # --------------------------------------------------------
    # 카드 이미지
    # --------------------------------------------------------

    card_image = card.get(
        "card_img"
    )

    image_url = None

    if isinstance(card_image, dict):

        image_url = card_image.get(
            "url"
        )

    # --------------------------------------------------------
    # 혜택 텍스트
    # --------------------------------------------------------

    benefit_text = collect_benefit_text(
        card
    )

    # --------------------------------------------------------
    # 주유 혜택
    # --------------------------------------------------------

    oil_sentences = find_oil_sentences(
        benefit_text
    )

    oil_benefit = parse_oil_benefit(
        oil_sentences
    )

    # --------------------------------------------------------
    # 최종 데이터
    # --------------------------------------------------------

    return {
        "card_id": card_id,

        "card_name": card.get(
            "name"
        ),

        "card_company": card_company,

        "brand": brand_name,

        "category": card.get(
            "cate_txt"
        ),

        "card_type": card.get(
            "c_type_txt"
        ),

        "card_image": image_url,

        "oil_benefit": oil_benefit
    }


# ============================================================
# 전체 카드 크롤링
# ============================================================

def crawl_all_cards():

    print("=" * 70)
    print("카드고릴라 전체 카드 API 크롤링 시작")
    print("=" * 70)

    print(
        f"페이지당 카드 수: {PER_PAGE}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # 첫 페이지
    # --------------------------------------------------------

    first = get_cards(
        1,
        PER_PAGE
    )

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

    total_pages = math.ceil(
        total / PER_PAGE
    )

    print(
        f"전체 카드 수: {total}"
    )

    print(
        f"1페이지 카드 수: {len(first_cards)}"
    )

    print(
        f"전체 페이지 수: {total_pages}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # 원본 카드 저장
    # --------------------------------------------------------

    all_cards = []

    all_cards.extend(
        first_cards
    )

    failed_pages = []

    # --------------------------------------------------------
    # 2페이지부터
    # --------------------------------------------------------

    for page in range(
        2,
        total_pages + 1
    ):

        result = get_cards(
            page,
            PER_PAGE
        )

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
            print("-" * 70)

            print(
                f"[WARNING] "
                f"{page}페이지 수집 실패"
            )

            print(
                "해당 페이지를 실패 목록에 기록하고 "
                "다음 페이지로 진행합니다."
            )

            print("-" * 70)

            failed_pages.append(
                page
            )

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

    raw_unique_cards = list(
        unique_cards.values()
    )

    # ========================================================
    # 우리 프로젝트용 데이터 변환
    # ========================================================

    simplified_cards = []

    for index, card in enumerate(
        raw_unique_cards,
        start=1
    ):

        simplified = simplify_card(
            card
        )

        simplified_cards.append(
            simplified
        )

        if index % 100 == 0:

            print(
                f"[정리] "
                f"{index}개 카드 변환 완료"
            )

    # ========================================================
    # 결과
    # ========================================================

    print()
    print("=" * 70)
    print("크롤링 종료")
    print("=" * 70)

    print(
        f"API 전체 카드 수 : {total}"
    )

    print(
        f"API 수집 카드 수 : {len(all_cards)}"
    )

    print(
        f"중복 제거 후 : {len(raw_unique_cards)}"
    )

    print(
        f"최종 카드 수 : {len(simplified_cards)}"
    )

    print(
        f"실패 페이지 수 : {len(failed_pages)}"
    )

    if failed_pages:

        print(
            f"실패 페이지 : {failed_pages}"
        )

    else:

        print(
            "모든 페이지 정상 수집"
        )

    # --------------------------------------------------------
    # 주유 혜택 통계
    # --------------------------------------------------------

    oil_cards = [
        card
        for card in simplified_cards
        if card["oil_benefit"]["has_benefit"]
    ]

    print(
        f"주유 혜택 카드 수 : "
        f"{len(oil_cards)}"
    )

    print("=" * 70)

    return {
        "source": "card-gorilla",
        "total": total,
        "collected": len(simplified_cards),
        "failed_page_count": len(
            failed_pages
        ),
        "failed_pages": failed_pages,
        "cards": simplified_cards
    }


# ============================================================
# JSON 저장
# ============================================================

def save_cards(result):

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

    print()
    print("=" * 70)
    print("cards.json 저장 완료")
    print("=" * 70)

    print(
        f"전체 카드 : "
        f"{result['total']}"
    )

    print(
        f"저장 카드 : "
        f"{result['collected']}"
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

    try:

        result = crawl_all_cards()

        save_cards(
            result
        )

        print()
        print(
            "크롤링 작업 정상 종료"
        )

    except Exception as e:

        print()
        print("=" * 70)
        print("크롤링 중 예외 발생")
        print("=" * 70)

        print(
            f"{type(e).__name__}: {e}"
        )

        raise


if __name__ == "__main__":

    main()
