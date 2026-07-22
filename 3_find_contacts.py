"""companies_filtered.csv'deki her firma icin web sitesini bulur ve e-posta arar.

Website bulma iki katmanli calisir (DuckDuckGo Turkiye'de ISS seviyesinde
engellenebiliyor, bu yuzden birincil kaynak Bing oldu):
  1) Bing arama sonuclari (Playwright ile)
  2) Bing sonuc vermezse, firma adindan tahmin edilen marka adiyla olasi
     domain adaylarini (.com.tr / .com) dogrudan ziyaret etmeyi dene

Website bulunduktan sonra bir dogrulama adimi calisir: firma adindan cikarilan
marka kelimesi, sitenin anasayfa icerginde (case-insensitive, Turkce karakter
normallestirmesiyle) geciyor mu diye kontrol edilir. Gecmiyorsa status
"mismatch" olarak isaretlenir (email bulunsa bile kaydedilmez).

Cikti: data/companies_contacts.csv
       name, sector, is_engineering, reason, website, source, email, status
status: found / no_website / no_email / mismatch / error
source: bing_search / domain_guess (website bulunamadiysa bos)
"""
import csv
import re
import time
from collections import Counter
from urllib.parse import urlencode, urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import Browser, BrowserContext, sync_playwright

from common import DATA_DIR, USER_AGENT, env_float, is_placeholder_email

INPUT_PATH = DATA_DIR / "companies_filtered.csv"
OUTPUT_PATH = DATA_DIR / "companies_contacts.csv"

REQUEST_DELAY = env_float("REQUEST_DELAY", 1.5)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

EXCLUDED_DOMAINS = (
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "wikipedia.org",
    "cyberpark.com.tr",
    "google.com",
    "maps.google.com",
    "bing.com",
)

CONTACT_PATH_HINTS = ("iletisim", "contact", "bize-ulasin", "hakkimizda", "about")

TR_ASCII_MAP = str.maketrans(
    {
        "ı": "i", "İ": "i",
        "ş": "s", "Ş": "s",
        "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u",
        "ö": "o", "Ö": "o",
        "ç": "c", "Ç": "c",
    }
)

GENERIC_NAME_WORDS = {
    "anonim", "sirketi", "as", "ltd", "sti", "limited",
    "sanayi", "ticaret", "ve", "teknoloji", "teknolojileri",
    "yazilim", "bilisim", "muhendislik", "danismanlik", "hizmetleri",
}


def extract_brand(company_name: str) -> str:
    """Firma adindan olasi domain markasini cikarir (orn. 'ACME YAZILIM A.S.' -> 'acme')."""
    ascii_lower = company_name.translate(TR_ASCII_MAP).lower()
    ascii_lower = re.sub(r"[.,]", "", ascii_lower)
    words = [w for w in ascii_lower.split() if w not in GENERIC_NAME_WORDS]
    if not words:
        return ""
    return re.sub(r"\s+", "", words[0])


def domain_candidates(brand: str) -> list[str]:
    return [
        f"https://{brand}.com.tr",
        f"https://{brand}.com",
        f"https://www.{brand}.com.tr",
        f"https://www.{brand}.com",
    ]


def bing_search(context: BrowserContext, query: str) -> list[str]:
    page = context.new_page()
    try:
        url = "https://www.bing.com/search?" + urlencode({"q": query})
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        try:
            page.wait_for_selector("li.b_algo h2 a", timeout=10000)
        except Exception:
            return []

        links = []
        for el in page.query_selector_all("li.b_algo h2 a"):
            href = el.get_attribute("href")
            if href:
                links.append(href)
        return links
    except Exception:
        return []
    finally:
        page.close()


def find_website_via_bing(context: BrowserContext, company_name: str) -> str | None:
    query = f"{company_name} cyberpark resmi web sitesi"
    for href in bing_search(context, query):
        domain = urlparse(href).netloc.lower()
        if not domain:
            continue
        if any(excluded in domain for excluded in EXCLUDED_DOMAINS):
            continue
        return f"{urlparse(href).scheme}://{urlparse(href).netloc}"
    return None


def find_website_via_domain_guess(context: BrowserContext, company_name: str) -> str | None:
    brand = extract_brand(company_name)
    if not brand:
        return None

    for candidate in domain_candidates(brand):
        page = context.new_page()
        try:
            response = page.goto(candidate, timeout=8000, wait_until="domcontentloaded")
            if response is not None and response.ok:
                return candidate
        except Exception:
            continue
        finally:
            page.close()

    return None


def guess_official_site(context: BrowserContext, company_name: str) -> tuple[str | None, str]:
    """Website'i once Bing aramasiyla, bulamazsa domain tahminiyle bulmaya calisir.

    Returns: (website_or_None, kaynak) - kaynak "bing_search", "domain_guess" veya "none"
    """
    website = find_website_via_bing(context, company_name)
    if website:
        return website, "bing_search"

    website = find_website_via_domain_guess(context, company_name)
    if website:
        return website, "domain_guess"

    return None, "none"


def brand_matches_site(brand: str, html: str) -> bool:
    """Bulunan sitenin gercekten aranan firmaya ait olup olmadigini dogrular:
    firma adindan cikarilan marka kelimesi sayfa iceriginde (case-insensitive,
    Turkce karakterler ASCII'ye normallestirilerek) geciyor mu diye bakar."""
    normalized_html = html.translate(TR_ASCII_MAP).lower()
    return brand.lower() in normalized_html


def extract_emails(html: str) -> set[str]:
    found = set(EMAIL_RE.findall(html))
    return {e for e in found if not is_placeholder_email(e)}


def get_subpage_links(page, base_url: str) -> list[str]:
    links = []
    for el in page.query_selector_all("a"):
        href = el.get_attribute("href")
        if not href:
            continue
        lower = href.lower()
        if any(hint in lower for hint in CONTACT_PATH_HINTS):
            links.append(urljoin(base_url, href))
    return list(dict.fromkeys(links))[:3]


def find_email_on_site(context: BrowserContext, website: str) -> tuple[str | None, str]:
    """Sitede e-posta arar. Ayrica anasayfa HTML'ini geri dondurur (dogrulama
    adiminda tekrar sayfa cekmemek icin, bu HTML tekrar kullanilir)."""
    page = context.new_page()
    try:
        page.goto(website, timeout=20000, wait_until="domcontentloaded")
        homepage_html = page.content()

        emails = extract_emails(homepage_html)
        if emails:
            return sorted(emails)[0], homepage_html

        for sub_url in get_subpage_links(page, website):
            try:
                page.goto(sub_url, timeout=20000, wait_until="domcontentloaded")
            except Exception:
                continue
            emails = extract_emails(page.content())
            if emails:
                return sorted(emails)[0], homepage_html
            time.sleep(REQUEST_DELAY)

        return None, homepage_html
    finally:
        page.close()


def main() -> None:
    with INPUT_PATH.open(encoding="utf-8-sig") as f:
        companies = list(csv.DictReader(f))

    if not companies:
        print("companies_filtered.csv bos veya bulunamadi. Once 2_classify_engineering.py calistirin.")
        return

    results = []

    with sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(headless=True)
        context: BrowserContext = browser.new_context(user_agent=USER_AGENT)

        try:
            for idx, company in enumerate(companies, start=1):
                name = company["name"]
                print(f"[contacts] {idx}/{len(companies)}: {name}")
                row = dict(company)
                row["website"] = ""
                row["source"] = ""
                row["email"] = ""
                row["status"] = "error"

                try:
                    website, source = guess_official_site(context, name)
                    time.sleep(REQUEST_DELAY)

                    if not website:
                        row["status"] = "no_website"
                        results.append(row)
                        print(f"  -> website: - | status: {row['status']}")
                        continue

                    row["website"] = website
                    row["source"] = source
                    email, homepage_html = find_email_on_site(context, website)
                    time.sleep(REQUEST_DELAY)

                    brand = extract_brand(name)
                    if brand and not brand_matches_site(brand, homepage_html):
                        row["status"] = "mismatch"
                    elif email:
                        row["email"] = email
                        row["status"] = "found"
                    else:
                        row["status"] = "no_email"

                except Exception as exc:  # noqa: BLE001
                    print(f"  hata: {exc}")
                    row["status"] = "error"

                results.append(row)
                print(f"  -> website: {row['website'] or '-'} | source: {row['source'] or '-'} | status: {row['status']}")
        finally:
            context.close()
            browser.close()

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name", "sector", "is_engineering", "reason",
                "website", "source", "email", "status",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    status_counts = Counter(r["status"] for r in results)
    found_count = status_counts.get("found", 0)
    print(f"\n{found_count} / {len(results)} firma icin e-posta bulundu -> {OUTPUT_PATH}")

    print("\nStatus dagilimi:")
    for status in ("found", "no_website", "no_email", "mismatch", "error"):
        print(f"  {status}: {status_counts.get(status, 0)}")


if __name__ == "__main__":
    main()
