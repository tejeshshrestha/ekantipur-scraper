import json
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Playwright


# Helper functions to loop through multiple attributes
def _first_text(scope, selectors):
    for selector in selectors:
        el = scope.query_selector(selector)
        if el:
            value = (el.text_content() or "").strip()
            if value:
                return value
    return None


def _first_attr(scope, selectors, attr):
    for selector in selectors:
        el = scope.query_selector(selector)
        if el:
            value = (el.get_attribute(attr) or "").strip()
            if value:
                return value
    return None


def scrape_entertainment(page):
    page.goto("https://ekantipur.com/entertainment")
    page.wait_for_selector("div.category")

    cards = page.query_selector_all("div.category")
    results = []

    for card in cards[:5]:
        title_el = card.query_selector("h2 a")
        title = title_el.text_content().strip() 
        # print(title)

        # try multiple selectors as fallback
        author_text = _first_text(card, ["div.author-name", ".author-name", ".author", ".byline"])

        image_url = _first_attr(
            card,
            ["div.category-image img", "div.category-image a img", "img"],
            "src",
        ) or _first_attr(
            card,
            ["div.category-image img", "div.category-image a img", "img"],
            "data-src",
        )
        
        href = title_el.get_attribute("href")

        category = None
        if href:
            # extract category from URL path
            parsed = urlparse(href)
            parts = [part for part in parsed.path.split("/") if part]
            if parts:
                category = parts[0]

        results.append(
            {
                "title": title,
                "image_url": image_url,
                "category": category,
                "author": author_text or None,
            }
        )
    return results


def scrape_cartoon(page):
    page.goto("https://ekantipur.com")

    page.wait_for_load_state("networkidle")
    page.wait_for_selector("div.section-news")

    # wait 2 secs for JS to initialize the swiper before accessing slides
    page.wait_for_timeout(2000)  

    
    section_candidates = page.query_selector_all("div.section-news")
    cartoon_section = None
    for section in section_candidates:
        section_name = _first_text(section, ["h4 a", "h4"])
        if section_name and "कार्टुन" in section_name:
            cartoon_section = section
            break

    if not cartoon_section:
        cartoon_section = page.query_selector("div.section-news") or page

    slider_scope = (
        cartoon_section.query_selector("div.cartoon-slider")
        or cartoon_section.query_selector("div.swiper-wrapper")
        or cartoon_section
    )

    slide = (
        slider_scope.query_selector("div.swiper-slide-active")
        or slider_scope.query_selector("div.swiper-slide")
        or slider_scope
    )

    # try multiple selectors as fallback
    title = _first_text(slide, ["h2 a", "h3 a", "h4 a", "a[title]", "img[alt]"])
    image_url = _first_attr(
        slide,
        ["img", "picture source", "a img"],
        "src",
    ) or _first_attr(
        slide,
        ["img", "picture source", "a img"],
        "data-src",
    )
    if not title:
        title = _first_attr(slide, ["img"], "alt")
    author = _first_text(slide, ["div.author-name", ".author-name", ".author", ".byline"])

    return {
        "title": title,
        "image_url": image_url,
        "author": author or None,
    }


def scrape(playwright: Playwright):
    chromium = playwright.chromium
    browser = chromium.launch(headless=False)
    page = browser.new_page()

    output = {
        "entertainment_news": scrape_entertainment(page),
        "cartoon_of_the_day": scrape_cartoon(page),
    }

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    browser.close()
    return output


if __name__ == "__main__":
    with sync_playwright() as playwright:
        data = scrape(playwright)
        # print(json.dumps(data, ensure_ascii=False, indent=2))