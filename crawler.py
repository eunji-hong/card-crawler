import json
import asyncio
from playwright.async_api import async_playwright

async def run():
    all_cards = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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

        print("🚀 Playwright 가상 브라우저로 카드고릴라 수집 시작...")

        for corp in corps:
            c_id = corp["id"]
            c_name = corp["name"]
            page_num = 1

            while page_num <= 5:  # 카드사별 최대 5페이지
                target_url = f"https://www.card-gorilla.com/search/card?corp={c_id}&page={page_num}"
                
                try:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2000)

                    card_elements = await page.query_selector_all(".card_name, span.card_name")
                    
                    if not card_elements:
                        break

                    added_count = 0
                    for elem in card_elements:
                        text = await elem.inner_text()
                        name = text.strip()
                        if name:
                            card_key = f"{c_name}_{name}".replace(" ", "_")
                            if not any(c["id"] == card_key for c in all_cards):
                                all_cards.append({
                                    "id": card_key,
                                    "name": name,
                                    "company": c_name
                                })
                                added_count += 1

                    print(f"[{c_name}] {page_num}페이지: {added_count}개 추가 (누적 {len(all_cards)}개)")
                    
                    if added_count == 0:
                        break
                        
                    page_num += 1

                except Exception as e:
                    print(f"[{c_name}] {page_num}페이지 실행 중 에러: {e}")
                    break

        await browser.close()

    return all_cards

if __name__ == "__main__":
    cards = asyncio.run(run())
    print(f"\n🎉 총 {len(cards)}개 카드 데이터 수집 완료!")
    
    with open("cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
