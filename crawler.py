# ==========================================
# 카드 더보기 반복 클릭
# ==========================================

print("카드 더보기 반복 수집 시작")

previous_count = 0
no_change_count = 0

while True:

    # 현재 카드 링크 수집
    card_links = await page.locator(
        'a[href*="/card/detail/"]'
    ).evaluate_all("""
        elements => [...new Set(
            elements
                .map(e => e.href)
                .filter(href => href.includes('/card/detail/'))
        )]
    """)

    current_count = len(card_links)

    print(f"현재 발견 카드: {current_count}개")

    # 카드가 더 이상 늘지 않는지 확인
    if current_count == previous_count:
        no_change_count += 1
    else:
        no_change_count = 0

    previous_count = current_count

    # 2번 연속 변화가 없으면 종료
    if no_change_count >= 2:
        print("새로운 카드가 더 이상 발견되지 않습니다.")
        break

    # ------------------------------------------
    # '카드 더보기' 찾기
    # ------------------------------------------

    more_button = page.get_by_text("카드 더보기", exact=True)

    if await more_button.count() == 0:
        print("카드 더보기 텍스트를 찾지 못했습니다.")
        break

    try:
        # 화면에 보이도록 이동
        await more_button.first.scroll_into_view_if_needed()

        # 클릭
        await more_button.first.click()

        print("카드 더보기 클릭")

        # AJAX 로딩 대기
        await page.wait_for_timeout(1500)

    except Exception as e:
        print(f"카드 더보기 클릭 실패: {e}")
        break
