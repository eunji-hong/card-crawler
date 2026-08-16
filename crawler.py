import json
import requests


API_URL = "https://api.card-gorilla.com:8080/v1/cards"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.card-gorilla.com/",
}


def main():

    print("=" * 70)
    print("카드고릴라 카드 API 테스트")
    print("=" * 70)

    params = {
        "p": 1,
        "perPage": 10,
        "is_discon": 0
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    print()
    print("REQUEST:")
    print(response.url)

    print()
    print("STATUS:")
    print(response.status_code)

    response.raise_for_status()

    data = response.json()

    print()
    print("RESPONSE:")
    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )[:10000]
    )

    # --------------------------------------------------
    # 응답 구조 확인
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("응답 구조")
    print("=" * 70)

    print(
        "TYPE:",
        type(data).__name__
    )

    if isinstance(data, dict):

        print(
            "KEYS:",
            list(data.keys())
        )

    elif isinstance(data, list):

        print(
            "LIST LENGTH:",
            len(data)
        )

    print()
    print("=" * 70)
    print("API 테스트 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
