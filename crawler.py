import requests
import json
import time

def fetch_cards_from_api():
    all_cards = []
    
    # 카드고릴라 내부 API 접근을 위한 헤더 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.card-gorilla.com/search/card"
    }

    # 카드고릴라 등록 주요 카드사 ID 목록
    corp_ids = [1, 2, 3, 4, 5, 7, 8, 9, 10]

    print("🚀 카드고릴라 API 데이터 직접 수집 시작...")

    for corp in corp_ids:
        page = 1
        while True:
            # 카드고릴라 실제 데이터 조회 API URL
            api_url = f"https://www.card-gorilla.com/api/cards?corp={corp}&page={page}&limit=50"
            
            try:
                res = requests.get(api_url, headers=headers, timeout=10)
                
                if res.status_code != 200:
                    print(f"카드사 ID {corp} 조회 응답 실패 (Status: {res.status_code})")
                    break
                    
                data = res.json()
                
                # 데이터 목록 추출
                card_list = data.get("data", []) if isinstance(data, dict) else []
                
                if not card_list:
                    break

                for card in card_list:
                    c_name = card.get("name") or card.get("card_name")
                    c_corp = card.get("corp_name") or card.get("corp") or "카드사"
                    c_id = card.get("id") or f"{c_corp}_{c_name}".replace(" ", "_")

                    if c_name:
                        all_cards.append({
                            "id": str(c_id),
                            "name": str(c_name).strip(),
                            "company": str(c_corp).strip()
                        })

                print(f"카드사 [{corp}] - {page}페이지 완료 ({len(card_list)}개 추가)")
                page += 1
                time.sleep(0.3) # 서버 부하 방지 대기

            except Exception as e:
                print(f"오류 발생 (corp: {corp}, page: {page}): {e}")
                break

    return all_cards

if __name__ == "__main__":
    cards = fetch_cards_from_api()
    print(f"\n🎉 총 {len(cards)}개 카드 데이터 수집 성공!")
    
    with open("cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
