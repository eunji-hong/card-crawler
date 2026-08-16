import asyncio
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
        print("CARD GORILLA DOM 진단")
        print("=" * 70)

        # --------------------------------------------------
        # 네트워크 요청
        # --------------------------------------------------

        def on_request(request):

            url = request.url.lower()

            # 불필요한 폰트/이미지 등 제외
            keywords = [
                "card",
                "search",
                "list",
                "ajax",
                "api",
                "json"
            ]

            if any(keyword in url for keyword in keywords):

                print(
                    "[REQUEST]",
                    request.method,
                    request.url
                )

                if request.method == "POST":

                    try:
                        print(
                            "[POST DATA]",
                            request.post_data
                        )
                    except Exception:
                        pass


        page.on(
            "request",
            on_request
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

        await page.wait_for_timeout(5000)

        print("페이지 로딩 완료")


        # --------------------------------------------------
        # 1. 페이지 텍스트 확인
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("1. 페이지에 '카드 더보기'가 존재하는지")
        print("=" * 70)

        text_count = await page.get_by_text(
            "카드 더보기",
            exact=True
        ).count()

        print(
            "정확히 '카드 더보기'인 요소:",
            text_count
        )


        # --------------------------------------------------
        # 2. 카드 더보기 관련 모든 요소
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("2. '카드 더보기' 관련 DOM")
        print("=" * 70)

        elements = await page.locator(
            "body *"
        ).evaluate_all(
            """
            elements => elements
                .filter(el => {
                    const text = (el.innerText || "").trim();
                    return text.includes("카드 더보기");
                })
                .slice(0, 20)
                .map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    className: el.className,
                    text: (el.innerText || "").trim().substring(0, 100),
                    outerHTML: el.outerHTML.substring(0, 1000)
                }))
            """
        )

        for index, element in enumerate(
            elements,
            start=1
        ):

            print()
            print(f"[{index}]")
            print("TAG:", element["tag"])
            print("ID:", element["id"])
            print("CLASS:", element["className"])
            print("TEXT:", element["text"])
            print("HTML:", element["outerHTML"])


        # --------------------------------------------------
        # 3. 카드 상세 링크
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("3. 현재 페이지의 카드 상세 링크")
        print("=" * 70)

        card_links = await page.locator(
            'a[href*="/card/detail/"]'
        ).evaluate_all(
            """
            elements => elements.map(a => ({
                href: a.href,
                text: (a.innerText || "").trim()
            }))
            """
        )

        print(
            "카드 상세 링크 수:",
            len(card_links)
        )

        for item in card_links[:20]:

            print(
                item["href"],
                "|",
                item["text"][:100]
            )


        # --------------------------------------------------
        # 4. HTML에서 card/detail 검색
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("4. HTML의 card/detail 개수")
        print("=" * 70)

        html = await page.content()

        print(
            "card/detail 등장 횟수:",
            html.count("/card/detail/")
        )


        # --------------------------------------------------
        # 5. 페이지의 script 확인
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("5. 카드 관련 JavaScript")
        print("=" * 70)

        scripts = await page.locator(
            "script"
        ).evaluate_all(
            """
            scripts => scripts.map(s => ({
                src: s.src,
                text: s.innerText
            }))
            """
        )

        for script in scripts:

            src = script["src"]

            text = script["text"]

            if (
                "card" in src.lower()
                or "search" in src.lower()
                or "card" in text.lower()
                or "more" in text.lower()
            ):

                print()
                print("SCRIPT SRC:")
                print(src)

                if text:

                    # 너무 길면 앞부분만
                    print(
                        text[:3000]
                    )


        # --------------------------------------------------
        # 6. 카드 더보기 클릭 전후 HTML 비교
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("6. 카드 더보기 클릭 테스트")
        print("=" * 70)

        before_html = await page.content()

        before_links = await page.locator(
            'a[href*="/card/detail/"]'
        ).count()

        print(
            "클릭 전 카드 링크:",
            before_links
        )


        # 카드 더보기 후보
        candidates = await page.locator(
            "button, a, div, span"
        ).evaluate_all(
            """
            elements => elements
                .filter(el => {
                    const text = (el.innerText || "").trim();

                    return text === "카드 더보기" ||
                           text.includes("카드 더보기");
                })
                .slice(0, 10)
                .map(el => ({
                    tag: el.tagName,
                    id: el.id,
                    className: el.className,
                    text: (el.innerText || "").trim(),
                    html: el.outerHTML.substring(0, 1500)
                }))
            """
        )

        print(
            "더보기 후보:",
            len(candidates)
        )


        if candidates:

            print()
            print("첫 번째 후보:")
            print(
                candidates[0]["html"]
            )

            # JS로 실제 클릭
            clicked = await page.evaluate(
                """
                () => {

                    const elements = Array.from(
                        document.querySelectorAll(
                            "button, a, div, span"
                        )
                    );

                    const target = elements.find(
                        el => {
                            const text =
                                (el.innerText || "").trim();

                            return text === "카드 더보기";
                        }
                    );

                    if (!target) {
                        return false;
                    }

                    target.scrollIntoView({
                        block: "center"
                    });

                    target.click();

                    return true;
                }
                """
            )

            print(
                "JS 클릭 결과:",
                clicked
            )

            await page.wait_for_timeout(
                3000
            )


            after_links = await page.locator(
                'a[href*="/card/detail/"]'
            ).count()

            print(
                "클릭 후 카드 링크:",
                after_links
            )


        # --------------------------------------------------
        # 종료
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("진단 완료")
        print("=" * 70)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
