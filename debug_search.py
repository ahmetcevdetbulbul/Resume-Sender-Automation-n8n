"""3_find_contacts.py icindeki iki katmanli website bulma mantigini
(guess_official_site: Bing arama + domain tahmini) tek bir ornek firma icin
manuel calistirip debug eden yardimci script.

headless=False ile tarayici gercekten acilir, gozle kontrol edebilirsin.
Her iki katmanin sonucu ayri ayri yazdirilir (Bing'den mi geldi, domain
tahmininden mi), Bing sonuc sayfasinin HTML'inin ilk 2000 karakteri ve
bulunan link sayisi terminale yazdirilir, ayrica data/debug_screenshot.png'ye
ekran goruntusu kaydedilir.

Kullanim:
    python debug_search.py
    python debug_search.py "Baska Firma Adi"
"""
import sys
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

import importlib

find_contacts = importlib.import_module("3_find_contacts")

from common import DATA_DIR, USER_AGENT

COMPANY_NAME = sys.argv[1] if len(sys.argv) > 1 else "ASELSAN"
SCREENSHOT_PATH = DATA_DIR / "debug_screenshot.png"


def main() -> None:
    query = f"{COMPANY_NAME} cyberpark resmi web sitesi"
    url = "https://www.bing.com/search?" + urlencode({"q": query})

    print(f"Firma: {COMPANY_NAME}")
    print(f"Sorgu: {query}")
    print(f"Bing URL: {url}\n")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(user_agent=USER_AGENT)

        # --- KATMAN 1: Bing arama sayfasini gorsel/HTML olarak incele ---
        page = context.new_page()
        try:
            try:
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
            except Exception as exc:  # noqa: BLE001
                print(f"UYARI: page.goto timeout/hata: {exc}")
                print("Yine de o ana kadar yuklenen HTML/ekran goruntusu alinacak.\n")

            try:
                page.wait_for_selector("li.b_algo h2 a", timeout=10000)
                found_selector = True
            except Exception as exc:  # noqa: BLE001
                found_selector = False
                print(f"UYARI: 'li.b_algo h2 a' selector'i beklenirken hata/timeout: {exc}\n")

            html = page.content()
            print("--- Bing HTML ilk 2000 karakter ---")
            print(html[:2000])
            print("--- /HTML ---\n")

            links = []
            for el in page.query_selector_all("li.b_algo h2 a"):
                href = el.get_attribute("href")
                if href:
                    links.append(href)

            print(f"'li.b_algo h2 a' selector bulundu mu: {found_selector}")
            print(f"Bulunan link sayisi: {len(links)}")
            for href in links[:10]:
                print(f"  - {href}")

            page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
            print(f"\nEkran goruntusu kaydedildi: {SCREENSHOT_PATH}")
        finally:
            page.close()

        # --- Iki katmanin tamamini gercek fonksiyonlarla calistir ---
        print("\n=== guess_official_site() sonucu (Bing -> domain tahmini) ===")
        website, source = find_contacts.guess_official_site(context, COMPANY_NAME)
        print(f"website: {website}")
        print(f"kaynak : {source}  (bing_search / domain_guess / none)")

        brand = find_contacts.extract_brand(COMPANY_NAME)
        print(f"\ntahmini marka adi: {brand!r}")
        print("denenecek domain adaylari:")
        for candidate in find_contacts.domain_candidates(brand):
            print(f"  - {candidate}")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
