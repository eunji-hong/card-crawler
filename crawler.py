import asyncio
from playwright.async_api import async_playwright


URL = "https://www.card-gorilla.com/search/card"


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print("=" * 70)
        print("CARD GORILLA JS 분석")
        print("=" * 70)

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        # --------------------------------------------------
        # 모든 script src
        # --------------------------------------------------

        scripts = await page.locator(
            "script[src]"
        ).evaluate_all(
            """
            scripts => scripts.map(s => s.src)
            """
        )

        print()
        print("JS 파일 수:", len(scripts))

        for src in scripts:

            if "card-gorilla.com/js/" not in src:
                continue

            print()
            print("=" * 70)
            print("JS:", src)
            print("=" * 70)

            try:

                # 브라우저의 fetch를 이용해서 JS 가져오기
                content = await page.evaluate(
                    """
                    async (url) => {
                        const response = await fetch(url);
                        return await response.text();
                    }
                    """,
                    src
                )

                print(
                    "JS 크기:",
                    len(content)
                )

                # ------------------------------------------
                # 카드 목록 관련 키워드
                # ------------------------------------------

                keywords = [
                    "cardList",
                    "card_list",
                    "cardlist",
                    "cardData",
                    "card_data",
                    "searchCard",
                    "search_card",
                    "getCard",
                    "get_card",
                    "more",
                    "moreList",
                    "loadMore",
                    "page",
                    "pageSize",
                    "limit",
                    "offset",
                    "axios",
                    "$axios",
                    "/api/",
                    "/search/"
                ]

                found = set()

                for keyword in keywords:

                    start = 0

                    while True:

                        index = content.find(
                            keyword,
                            start
                        )

                        if index == -1:
                            break

                        found.add(index)

                        start = index + len(keyword)

                print(
                    "관련 코드 발견:",
                    len(found)
                )

                # ------------------------------------------
                # 발견된 부분 앞뒤 500자 출력
                # ------------------------------------------

                for index in sorted(found)[:30]:

                    print()
                    print("-" * 70)

                    start = max(
                        0,
                        index - 500
                    )

                    end = min(
                        len(content),
                        index + 1000
                    )

                    print(
                        content[start:end]
                    )

            except Exception as e:

                print(
                    "JS 분석 실패:",
                    e
                )

        print()
        print("=" * 70)
        print("분석 완료")
        print("=" * 70)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
