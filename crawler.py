import json
import asyncio
from playwright.async_api import async_playwright

async def run():
    all_cards = []
    card_index = 1
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900}
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

        print("🚀 카드고릴라 전체 목록 '더보기' 정밀 수집 시작...")

        for corp in corps:
            c_id = corp["id"]
            c_name = corp["name"]
            target_url = f"https://www.card-gorilla.com/search/card?corp={c_id}"

            try:
                await page.goto(target_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)

                # 카드 더보기 버튼 반복 클릭 (최대 30회)
                for i in range(30):
                    # 1. 화면을 최하단으로 스크롤하여 더보기 버튼 노출
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)

                    # 2. 이미지 속 '카드 더보기' 버튼 요소 탐색 (다양한 선택자 대응)
                    more_btn = await page.query_selector("div.btn_more, .more_btn, div:has-text('카드 더보기'), a:has-text('카드 더보기')")

                    if more_btn and await more_btn.is_visible():
                        # JS로 강제 클릭 수행
                        await page.evaluate("(el) => el.click()", more_btn)
                        
                        # 3. 데이터가 화면에 추가될 때까지 networkidle 및 충분한 대기
                        try:
                            await page.wait_for_load_state("networkidle", timeout=5000)
                        except:
                            pass
                        await page.wait_for_timeout(1500)
                    else:
                        # 더 이상 버튼이 보이지 않으면 누적 완료로 간주하고 탈출
                        break

                # 4. 펼쳐진 전체 카드 항목 수집
                card_items = await page.query_selector_all(".card_list > li, ul.lst > li, .lst_type1 > li")
                
                corp_added = 0
                for item in card_items:
                    name_elem = await item.query_selector(".card_name, span.card_name, p.name")
                    if name_elem:
                        name_text = await name_elem.inner_text()
                        card_name = name_text.strip()

                        # 중복 및 잘못된 텍스트 제외
                        if card_name and card_name not in ["카드 더보기", "자세히 보기"]:
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
                print(f"[{c_name}] 수집 오류: {e}")

        await browser.close()

    return all_cards

if __name__ == "__main__":
    cards = asyncio.run(run())
    print(f"\n🎉 총 {len(cards)}개 카드 데이터 최종 수집 완료!")
    
    with open("cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
