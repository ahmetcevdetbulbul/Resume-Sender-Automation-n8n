"""Cyberpark firma arşivi sayfalarını gezip firma listesini çıkarır.

Playwright ile headless Chromium kullanır (Cloudflare/JS korumasını asar).

Çıktı: data/companies_raw.csv (name, sector, source_page)
"""
import csv
import time

from bs4 import BeautifulSoup
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from common import DATA_DIR, USER_AGENT, env, env_int, env_float

BASE_URL = env("BASE_URL", "https://www.cyberpark.com.tr/firma-arsiv")
START_PAGE = env_int("START_PAGE", 1)
END_PAGE = env_int("END_PAGE", 19)
REQUEST_DELAY = env_float("REQUEST_DELAY", 1.5)

OUTPUT_PATH = DATA_DIR / "companies_raw.csv"


def fetch_page(page: Page, page_no: int) -> str:
    url = f"{BASE_URL}/{page_no}"
    page.goto(url, timeout=30000)
    page.wait_for_load_state("networkidle")
    return page.content()


def parse_companies(html: str, page_no: int) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    companies = []
    for item in soup.select("div.item"):
        title_el = item.select_one("h3.title")
        if not title_el:
            continue
        name = title_el.get_text(strip=True)
        if not name:
            continue
        sector_el = item.select_one("p")
        sector = sector_el.get_text(strip=True) if sector_el else ""
        companies.append({"name": name, "sector": sector, "source_page": page_no})
    return companies


def main() -> None:
    seen = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        try:
            for page_no in range(START_PAGE, END_PAGE + 1):
                print(f"[scrape] sayfa {page_no}/{END_PAGE}...")
                try:
                    html = fetch_page(page, page_no)
                except PlaywrightTimeoutError as exc:
                    print(f"  hata: sayfa {page_no} zaman asimina ugradi ({exc})")
                    time.sleep(REQUEST_DELAY)
                    continue
                except Exception as exc:  # noqa: BLE001
                    print(f"  hata: sayfa {page_no} alinamadi ({exc})")
                    time.sleep(REQUEST_DELAY)
                    continue

                companies = parse_companies(html, page_no)
                print(f"  {len(companies)} firma bulundu")

                for company in companies:
                    key = company["name"].strip().lower()
                    if key not in seen:
                        seen[key] = company

                time.sleep(REQUEST_DELAY)
        finally:
            context.close()
            browser.close()

    rows = list(seen.values())
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "sector", "source_page"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nToplam {len(rows)} tekil firma -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
