import json
import urllib.request

def run():
    all_cards = []
    card_index = 1

    corps = [
        {"id": "1", "name": "신한카드"},
        {"id": "2", "name": "삼성카드"},
        {"id": "3", "name": "KB국민카드"},
        {"id": "4", "name": "현대카드"},
        {"id": "5", "name": "롯데카드"},
        {"id": "7", "name": "하나카드"},
        {"id": "8", "name": "우리카드"},
        {"id": "9", "name": "NH농협카드"}
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    print("🚀 API 고속 수집 시작...")

    for corp in corps:
        c_id = corp["id"]
        c_name = corp["name"]
        page_num = 1
        corp_added = 0

        while page_num <= 30:
            api_url = f"https://www.card-gorilla.com/api/search/card?corp={c_id}&page={page_num}&limit=20"

            try:
                req = urllib.request.Request(api_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    card_list = data if isinstance(data, list) else data.get("data", [])

                    if not card_list:
                        break

                    for card in card_list:
                        card_name = card.get("name") or card.get("card_name")
                        if card_name:
                            if not any(c["name"] == card_name and c["company"] == c_name for c in all_cards):
                                all_cards.append({
                                    "id": str(card_index),
                                    "name": card_name.strip(),
                                    "company": c_name
                                })
                                card_index += 1
                                corp_added += 1

                    page_num += 1

            except Exception:
                break

        print(f"[{c_name}] 수집 완료: {corp_added}개 추가 (누적 {len(all_cards)}개)")

    return all_cards

if __name__ == "__main__":
    cards = run()
    print(f"\n🎉 총 {len(cards)}개 카드 데이터 고속 수집 완료!")
    
    with open("cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
