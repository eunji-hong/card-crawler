import json
import asyncio
from playwright.async_api import async_playwright

async def run():
    all_cards = []
    card_index = 1
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        page = await context.new_page()

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

        print("🚀 카드고릴라 '더보기' 클릭 방식 수집 시작...")

        for corp in corps:
            c_id = corp["id"]
            c_name = corp["name"]
            target_url = f"https://m.card-gorilla.com/search/card?corp={c_id}"

            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # '카드 더보기' 버튼이 있는 동안 계속 클릭해서 모든 카드 펼치기
                click_count = 0
                while click_count < 30: # 최대 30번 클릭 탐색
                    more_btn = await page.query_selector("button:has-text('카드 더보기'), .btn_more, .more_btn")
                    
                    if more_btn and await more_btn.is_visible():
                        await more_btn.click()
                        await page.wait_for_timeout(1000) # 더보기 로딩 대기
                        click_count += 1
                    else:
                        break

                # 화면에 있는 카드 아이템 요소들 가져오기
                # 보내주신 이미지 기준 카드명 요소 탐색
                card_blocks = await page.query_selector_all("div:has(> .card_name), .card_info, li")
                
                corp_added = 0
                for block in card_blocks:
                    # 카드 이름 추출
                    name_elem = await block.query_selector(".card_name, p.name, strong")
                    
                    if name_elem:
                        name_text = await name_elem.inner_text()
                        card_name = name_text.strip()

                        # 잘못 들어온 텍스트(예: '카드 더보기', '자세히 보기') 제외
                        if card_name and card_name not in ["자세히 보기", "카드 더보기", "온라인 신규회원 연회비 100% 캐시백"]:
                            # 중복 방지
                            if not any(c["name"] == card_name and c["company"] == c_name for c in all_cards):
                                all_cards.append({
                                    "id": str(card_index),
                                    "name": card_name,
                                    "company": c_name
                                })
                                card_index += 1
                                corp_added += 1

                print(f"[{c_name}] 수집 완료: {corp_added}개 추가 (누적 {len(all_cards)}개)")

            except Exception as e:
                print(f"[{c_name}] 수집 중 에러: {e}")

        await browser.close()

    return all_cards

if __name__ == "__main__":
    cards = asyncio.run(run())
    print(f"\n🎉 총 {len(cards)}개 카드 데이터 최종 수집 완료!")
    
    with open("cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
