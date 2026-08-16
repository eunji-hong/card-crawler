import json
import asyncio
from playwright.async_api import async_playwright

async def run():
    all_cards = []
    card_index = 1
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
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

        print("🚀 카드고릴라 수집 시작...")

        for corp in corps:
            c_id = corp["id"]
            c_name = corp["name"]
            target_url = f"https://www.card-gorilla.com/search/card?corp={c_id}"

            try:
                await page.goto(target_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(1500)

                # 더보기 버튼 반복 클릭 (최대 20회)
                for _ in range(20):
                    # 현재 카드 개수 측정
                    items_before = await page.query_selector_all(".card_list > li")
                    count_before = len(items_before)

                    # 카드 더보기 버튼 정확한 요소 찾기
                    more_btn = await page.query_selector("a.lst_more")
                    
                    if not more_btn:
                        # 대안 선택자
                        more_btn = await page.query_selector(".btn_more a, div.btn_more")

                    if more_btn and await more_btn.is_visible():
                        # 버튼 위치로 스크롤 이동 후 클릭
                        await more_btn.scroll_into_view_if_needed()
                        await page.wait_for_timeout(300)
                        await page.evaluate("(el) => el.click()", more_btn)

                        # 데이터 추가 로딩 대기 (최대 4초간 카드 수 증가 여부 체크)
                        loaded = False
                        for _ in range(8):
                            await page.wait_for_timeout(500)
                            items_after = await page.query_selector_all(".card_list > li")
                            if len(items_after) > count_before:
                                loaded = True
                                break
                        
                        # 클릭 후에도 개수가 늘어나지 않으면 종료
                        if not loaded:
                            break
                    else:
                        break

                # 로드된 카드 데이터 추출
                card_items = await page.query_selector_all(".card_list > li")
                corp_added = 0

                for item in card_items:
                    name_elem = await item.query_selector(".card_name")
                    if name_elem:
                        name_text = await name_elem.inner_text()
                        card_name = name_text.strip()

                        if card_name and card_name not in ["카드 더보기", "자세히 보기"]:
                            if not any(c["name"] == card_name and c["company"] == c_name for c in all_cards):
                                all_cards.append({
                                    "id": str(card_index),
                                    "name": card_name,
                                    "company": c_name
                                })
                                card_index += 1
                                corp_added += 1

                print(f"[{c_name}] 수집 완료: {corp_added}개 (누적 {len(all_cards)}개)")

            except Exception as e:
                print(f"[{c_name}] 에러 발생: {e}")

        await browser.close()

    return all_cards

if __name__ == "__main__":
    cards = asyncio.run(run())
    print(f"\n🎉 총 {len(cards)}개 카드 데이터 수집 완료!")
    
    with open("cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
