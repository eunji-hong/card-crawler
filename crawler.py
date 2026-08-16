import json
import re
import time
from pathlib import Path

import requests


API_BASE = "https://api.card-gorilla.com:8080/v1"

CARDS_URL = f"{API_BASE}/cards"

OUTPUT_FILE = Path("cards.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.card-gorilla.com/search/card",
}


def get_json(url, params=None):

    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    print(
        "GET",
        response.url,
        "→",
        response.status_code
    )

    response.raise_for_status()

    return response.json()


def find_card_list(data):
    """
    API 응답 안에서 카드 배열을 자동으로 찾는다.
    """

    if isinstance(data, list):

        if len(data) == 0:
            return None

        # 카드 객체처럼 보이는지 확인
        if any(
            isinstance(item, dict)
            for item in data
        ):
            return data

    if isinstance(data, dict):

        # 흔히 사용하는 배열 key 우선 탐색
        keys = [
            "data",
            "cards",
            "items",
            "results",
            "list",
            "rows",
        ]

        for key in keys:

            value = data.get(key)

            if isinstance(value, list):

                if len(value) > 0:
                    return value

        # 중첩 구조까지 탐색
        for value in data.values():

            if isinstance(value, dict):

                result = find_card_list(value)

                if result:
                    return result

            elif isinstance(value, list):

                if (
                    len(value) > 0
                    and isinstance(value[0], dict)
                ):
                    return value

    return None


def get_card_id(card):

    if not isinstance(card, dict):
        return None

    possible_keys = [
        "idx",
        "id",
        "card_idx",
        "cardId",
        "card_id",
        "no",
    ]

    for key in possible_keys:

        value = card.get(key)

        if value is not None:

            # 숫자 ID
            if str(value).isdigit():

                return str(value)

    return None


def get_card_name(card):

    if not isinstance(card, dict):
        return ""

    possible_keys = [
        "name",
        "card_name",
        "cardName",
        "title",
    ]

    for key in possible_keys:

        value = card.get(key)

        if value:

            return str(value)

    return ""


def test_api_parameters():

    print()
    print("=" * 70)
    print("카드 목록 API 파라미터 탐색")
    print("=" * 70)

    # ------------------------------------------------------
    # 이미 확인된 전체 카드 수
    # ------------------------------------------------------

    summary = get_json(
        CARDS_URL,
        {
            "summaryOnly": "true"
        }
    )

    print()
    print("SUMMARY:")
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2
        )
    )

    total = summary.get(
        "total",
        0
    )

    print()
    print("전체 카드 수:", total)

    # ------------------------------------------------------
    # 실제 목록을 가져올 가능성이 있는 파라미터 조합
    # ------------------------------------------------------

    candidates = [

        {
            "page": 1,
            "perPage": 30,
        },

        {
            "page": 0,
            "perPage": 30,
        },

        {
            "page": 1,
            "perPage": 100,
        },

        {
            "page": 0,
            "perPage": 100,
        },

        {
            "page": 1,
            "limit": 30,
        },

        {
            "page": 0,
            "limit": 30,
        },

        {
            "page": 1,
            "size": 30,
        },

        {
            "page": 0,
            "size": 30,
        },

        {
            "page": 1,
            "per_page": 30,
        },

        {
            "page": 0,
            "per_page": 30,
        },

    ]

    for params in candidates:

        print()
        print(
            "테스트:",
            params
        )

        try:

            data = get_json(
                CARDS_URL,
                params
            )

            print(
                "응답 형태:",
                type(data).__name__
            )

            if isinstance(data, dict):

                print(
                    "응답 key:",
                    list(data.keys())[:30]
                )

            cards = find_card_list(
                data
            )

            if cards:

                print(
                    "★ 카드 배열 발견:",
                    len(cards)
                )

                print(
                    json.dumps(
                        cards[0],
                        ensure_ascii=False,
                        indent=2
                    )[:3000]
                )

                return params, cards

        except Exception as e:

            print(
                "실패:",
                e
            )

    return None, None


def crawl_all_cards():

    params, first_cards = test_api_parameters()

    if not first_cards:

        print()
        print("=" * 70)
        print("실제 카드 목록 API 파라미터를 찾지 못했습니다.")
        print("=" * 70)

        return []

    print()
    print("=" * 70)
    print("카드 목록 API 확인")
    print("=" * 70)

    print(
        "사용 파라미터:",
        params
    )

    # ------------------------------------------------------
    # page 기반으로 전체 카드 수집
    # ------------------------------------------------------

    per_page = (
        params.get("perPage")
        or params.get("limit")
        or params.get("size")
        or params.get("per_page")
        or 30
    )

    all_cards = []

    page = params.get(
        "page",
        1
    )

    # 첫 페이지
    current_cards = first_cards

    while True:

        print()
        print(
            f"페이지 {page}: "
            f"{len(current_cards)}개"
        )

        all_cards.extend(
            current_cards
        )

        # 카드가 페이지 크기보다 적으면 마지막
        if len(current_cards) < per_page:

            print(
                "마지막 페이지로 판단"
            )

            break

        page += 1

        next_params = dict(
            params
        )

        next_params["page"] = page

        try:

            data = get_json(
                CARDS_URL,
                next_params
            )

            current_cards = find_card_list(
                data
            )

            if not current_cards:

                print(
                    "더 이상 카드가 없어 종료"
                )

                break

        except Exception as e:

            print(
                "페이지 요청 실패:",
                e
            )

            break

        time.sleep(
            0.2
        )

    # ------------------------------------------------------
    # ID 기준 중복 제거
    # ------------------------------------------------------

    unique = {}

    for card in all_cards:

        card_id = get_card_id(
            card
        )

        if card_id:

            unique[card_id] = card

    result = list(
        unique.values()
    )

    print()
    print("=" * 70)
    print("수집 결과")
    print("=" * 70)

    print(
        "API에서 받은 카드:",
        len(all_cards)
    )

    print(
        "중복 제거 후:",
        len(result)
    )

    return result


def main():

    cards = crawl_all_cards()

    if not cards:

        print(
            "카드를 가져오지 못했습니다."
        )

        return

    with open(
        OUTPUT_FILE,
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
    print("=" * 70)
    print(
        f"{OUTPUT_FILE} 저장 완료"
    )
    print(
        f"카드 수: {len(cards)}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
