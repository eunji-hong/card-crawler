import json
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def run():
    all_cards = []
    card_index = 1
    
    async with async_playwright() as p:
        # 봇 감지 방지를 위한 Chromium 브라우저 인자 설정
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
            locale="ko-KR"
        )
        page = await context.new_page()
        
        # Stealth 적용 (navigator.webdriver 차단 우회)
        await stealth_async(page)

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

        print("🚀 Stealth 모드로 카드고릴라 우회 수집 시작...")

        for corp in corps:
            c_id = corp["id"]
            c_name = corp["name"]
            target_url = f"https://www.card-gorilla.com/search/card?corp={c_id}"

            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2500)

                # '카드 더보기' 버튼을 감지하여 끝까지 확장 (최대 25회)
                for _ in range(25):
                    # 하단으로 스크롤하여 더보기 버튼 활성화
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)

                    # 카드 더보기 버튼 감지
                    more_btn = await page.query_selector("a.btn_more, div.btn_more, .more_btn, button:has-text('카드 더보기'), a:has-text('카드 더보기')")
                    
                    if more_btn and await more_btn.is_visible():
                        await page.evaluate("(el) => el.click()", more_btn)
                        await page.wait_for_timeout(1500)
                    else:
                        break

                # 전체 로드된 카드 DOM 요소 수집
                card_items = await page.query_selector_all(".card_list > li, ul.lst > li, .lst_type1 > li")
                
                corp_added = 0
                for item in card_items:
                    name_elem = await item.query_selector(".card_name, span.card_name, p.name")
                    if name_elem:
                        name_text = await name_elem.inner_text()
                        card_name = name_text.strip()

                        # 예외 텍스트 및 중복 검사
                        if card_name and card_name not in ["카드 더보기", "자세히 보기", "온라인 신규회원 연회비 100% 캐시백"]:
                            if not any(c["name"] == card_name and c["company"] == c_name for c in all_cards):
                                all_cards.append({
                                    "id": str(card_index),
                                    "name": card_name,
                                    "company": c_name
                                })
                                card_index += 1
                                corp_added += 1

                print(f"[{c_name}] 수집 성공: {corp_added}개 (누적 {len(all_cards)}개)")

            except Exception as e:
                print(f"[{c_name}] 수집 중 에러: {e}")

        await browser.close()

    return all_cards

if __name__ == "__main__":
    cards = asyncio.run(run())
    print(f"\n🎉 총 {len(cards)}개 카드 데이터 정상 수집 완료!")
    
    with open("cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
