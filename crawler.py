import asyncio
from playwright.async_api import async_playwright


URL = "https://www.card-gorilla.com/search/card"


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        # 모든 네트워크 요청 출력
        page.on(
            "request",
            lambda request: print(
                "REQUEST:",
                request.method,
                request.url
            )
        )

        page.on(
            "response",
            lambda response: print(
                "RESPONSE:",
                response.status,
                response.url
            )
        )

        print("=" * 60)
        print("카드고릴라 접속")
        print("=" * 60)

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        print("페이지 로딩 완료")

        await page.wait_for_timeout(5000)

        print("=" * 60)
        print("카드 더보기 찾기")
        print("=" * 60)

        buttons = await page.get_by_text(
            "카드 더보기",
            exact=True
        ).count()

        print("카드 더보기 개수:", buttons)

        print("=" * 60)
        print("완료")
        print("=" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
