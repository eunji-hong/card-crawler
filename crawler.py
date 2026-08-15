import requests
from bs4 import BeautifulSoup
import json
import time

def fetch_all_cardgorilla_cards():
    all_cards = []
    
    # 웹사이트 차단 방지용 헤더
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 주요 카드사 코드/이름 목록 (주요 카드사를 순회하며 전체 카드를 가져옵니다)
    # 카드고릴라 기준 주요 카드사 ID 목록
    card_corps = [
        {"id": "1", "name": "신한카드"},
        {"id": "2", "name": "삼성카드"},
        {"id": "3", "name": "KB국민카드"},
        {"id": "4", "name": "현대카드"},
        {"id": "5", "name": "롯데카드"},
        {"id": "7", "name": "하나카드"},
        {"id": "8", "name": "우리카드"},
        {"id": "9", "name": "NH농협카드"},
        {"id": "10", "name": "IBK기업은행"},
    ]

    print("🚀 전체 카드 수집을 시작합니다...")

    for corp in card_corps:
        page = 1
        corp_id = corp["id"]
        corp_name = corp["name"]
        
        while True:
            # 카드사별 전체 카드 목록 페이지 URL (페이지 번호 변경)
            url = f"https://www.card-gorilla.com/search/card?corp={corp_id}&page={page}"
            
            try:
                response = requests.get(url, headers=headers)
                soup = BeautifulSoup(response.text, "html.parser")
                
                # 카드 아이템 추출
                card_items = soup.select(".card_list > li")
                
                # 더 이상 카드가 없거나 페이지가 끝나면 다음 카드사로 이동
                if not card_items:
                    break
                
                has_new_card = False
                for item in card_items:
                    name_tag = item.select_one(".card_name")
                    
                    if name_tag:
                        card_name = name_tag.text.strip()
                        # 고유 식별자 생성 (예: 신한카드_신한_Deep_Dream)
                        card_id = f"{corp_name}_{card_name}".replace(" ", "_")
                        
                        # 중복 방지
                        if not any(c["id"] == card_id for c in all_cards):
                            all_cards.append({
                                "id": card_id,
                                "name": card_name,
                                "company": corp_name
                            })
                            has_new_card = True
                
                # 이 페이지에 새로 추가된 카드가 없으면 다음 카드사로
                if not has_new_card:
                    break
                    
                print(f"[{corp_name}] {page}페이지 수집 완료... (누적 {len(all_cards)}개)")
                page += 1
                time.sleep(0.5) # 서버 부하 방지를 위한 매너 대기 (0.5초)

            except Exception as e:
                print(f"[{corp_name}] {page}페이지 수집 중 에러: {e}")
                break

    return all_cards

if __name__ == "__main__":
    card_data = fetch_all_cardgorilla_cards()
    
    # 결과를 cards.json에 저장
    with open("cards.json", "w", encoding="utf-8") as f:
        json.dump(card_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n🎉 모든 수집 완료! 총 {len(card_data)}개의 전체 카드가 저장되었습니다.")
