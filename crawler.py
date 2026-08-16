import requests
import json
import time

def fetch_all_cards():
    all_cards = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.card-gorilla.com/"
    }

    # 카드고릴라 주요 카드사 ID
    corp_ids = ["1", "2", "3", "4", "5", "7", "8", "9", "10"]

    print("🚀 카드고릴라 데이터 수집을 시작합니다...")

    for corp in corp_ids:
        page = 1
        while True:
            # 카드고릴라 내부 검색 API
            api_url = f"https://www.card-gorilla.com/api/search/card?corp={corp}&page={page}&limit=20"
            
            try:
                res = requests.get(api_url, headers=headers, timeout=10)
                
                # API 응답이 정상(200)이 아니면 다음 카드사로 이동
                if res.status_code != 200:
                    break
                    
                data = res.json()
                
                # 응답 형태에 따른 카드 데이터 추출
                cards_data = data.get("data", []) if isinstance(data, dict) else data
                
                if not cards_data:
                    break

                for card in cards_data:
                    c_name = card.get("name") or card.get("card_name")
                    c_corp = card.get("corp_name") or card.get("corp") or "카드사"
                    c_id = card.get("id") or f"{c_corp}_{c_name}".replace(" ", "_")

                    if c_name:
                        all_cards.append({
                            "id": str(c_id),
                            "name": str(c_name).strip(),
                            "company": str(c_corp).strip()
                        })

                print(f"카드사 ID [{corp}] - {page}페이지 완료 (누적 {len(all_cards)}개)")
                page += 1
                time.sleep(0.3)

            except Exception as e:
                print(f"오류 발생 (corp: {corp}, page: {page}): {e}")
                break

    return all_cards

if __name__ == "__main__":
    cards = fetch_all_cards()
    
    print(f"\n총 {len(cards)}개 수집 성공!")
    
    with open("cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
