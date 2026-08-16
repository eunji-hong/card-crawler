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
        print("CARD GORILLA 실제 API 요청 확인")
        print("=" * 70)

        async def on_request(request):

            if "/v1/cards" in request.url:

                print()
                print("=" * 70)
                print("★ 실제 카드 API 요청 발견")
                print("=" * 70)

                print("METHOD:")
                print(request.method)

                print("URL:")
                print(request.url)

                print("POST DATA:")
                print(request.post_data)

                print("HEADERS:")
                print(
                    request.headers
                )

        page.on(
            "request",
            on_request
        )

        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(
            15000
        )

        print()
        print("=" * 70)
        print("완료")
        print("=" * 70)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
