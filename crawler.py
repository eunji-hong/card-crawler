import asyncio
import json
from playwright.async_api import async_playwright


URL = "https://www.card-gorilla.com/search/card"


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            viewport={
                "width": 1440,
                "height": 1200
            }
        )

        print("=" * 70)
        print("CARD GORILLA API 분석")
        print("=" * 70)

        # --------------------------------------------------
        # 모든 응답 감시
        # --------------------------------------------------

        async def response_handler(response):

            request = response.request

            if request.resource_type not in [
                "xhr",
                "fetch"
            ]:
                return

            url = response.url

            print()
            print("-" * 70)
            print("REQUEST")
            print(request.method)
            print(url)

            # GET이면 query string도 확인
            if request.method == "GET":
                print("GET URL:", url)

            # POST이면 body 확인
            if request.method == "POST":

                try:
                    print(
                        "POST DATA:",
                        request.post_data
                    )
                except Exception:
                    pass

            # 응답 확인
            try:

                content_type = response.headers.get(
                    "content-type",
                    ""
                )

                print(
                    "STATUS:",
                    response.status
                )

                print(
                    "CONTENT-TYPE:",
                    content_type
                )

                # JSON만 확인
                if (
                    "json" in content_type.lower()
                    or "javascript" not in content_type.lower()
                ):

                    try:

                        text = await response.text()

                        # 너무 긴 응답은 앞부분만
                        print(
                            "RESPONSE:",
                            text[:5000]
                        )

                    except Exception as e:

                        print(
                            "응답 읽기 실패:",
                            e
                        )

            except Exception as e:

                print(
                    "응답 분석 실패:",
                    e
                )


        page.on(
            "response",
            lambda response: asyncio.create_task(
                response_handler(response)
            )
        )


        # --------------------------------------------------
        # 페이지 접속
        # --------------------------------------------------

        print()
        print("페이지 접속")

        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print(
            "HTML 로딩 완료"
        )

        # Vue 초기화 기다리기
        await page.wait_for_timeout(
            10000
        )


        # --------------------------------------------------
        # 현재 URL / 제목
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("페이지 정보")
        print("=" * 70)

        print(
            "URL:",
            page.url
        )

        print(
            "TITLE:",
            await page.title()
        )


        # --------------------------------------------------
        # Vue 데이터 확인
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("Vue 상태 확인")
        print("=" * 70)

        vue_info = await page.evaluate(
            """
            () => {

                const app =
                    document.querySelector("#q-app");

                return {
                    exists: !!app,
                    text: app
                        ? app.innerText.substring(0, 3000)
                        : ""
                };
            }
            """
        )

        print(
            json.dumps(
                vue_info,
                ensure_ascii=False,
                indent=2
            )
        )


        # --------------------------------------------------
        # 카드 링크
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("현재 카드 링크")
        print("=" * 70)

        links = await page.locator(
            'a[href*="/card/detail/"]'
        ).evaluate_all(
            """
            elements => [
                ...new Set(
                    elements.map(a => a.href)
                )
            ]
            """
        )

        print(
            "카드 링크:",
            len(links)
        )

        for link in links:

            print(
                link
            )


        # --------------------------------------------------
        # 충분히 기다린 후 종료
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("API 분석 종료")
        print("=" * 70)

        await page.wait_for_timeout(
            3000
        )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
