"""companies_raw.csv icindeki firmalari OpenAI ile muhendislik/degil diye siniflandirir.

Cikti: data/companies_filtered.csv (sadece is_engineering=true olanlar)
       name, sector, is_engineering, reason
"""
import csv
import json

from openai import OpenAI

from common import DATA_DIR, env

INPUT_PATH = DATA_DIR / "companies_raw.csv"
OUTPUT_PATH = DATA_DIR / "companies_filtered.csv"

MODEL = env("OPENAI_MODEL", "gpt-4o-mini")
BATCH_SIZE = 25

ACADEMIC_KEYWORDS = (
    "ÜNİVERSİTE",
    "ENSTİTÜ",
    "ARAŞTIRMA MERKEZİ",
    "TÜBİTAK",
    "BİLKENT NANOTAM",
    "UNAM",
    "UMRAM",
    "NANOTAM",
)


def turkish_upper(text: str) -> str:
    # Python'un varsayilan str.upper() Turkce 'i' -> 'İ' donusumunu yapmaz
    # (ASCII 'I' uretir), bu yuzden anahtar kelime karsilastirmasi once
    # Turkce harfleri elle isaretleyip sonra upper() cagirir.
    return text.replace("i", "İ").replace("ı", "I").upper()


def is_academic_institution(name: str) -> bool:
    upper_name = turkish_upper(name)
    return any(keyword in upper_name for keyword in ACADEMIC_KEYWORDS)

SYSTEM_PROMPT = """Sen bir teknoloji parkı (Cyberpark) firma dizinini sınıflandıran bir asistansın.
Görevin: her firmanın MÜHENDİSLİK alanıyla ilgili bir şirket olup olmadığına karar vermek.

MÜHENDİSLİK SAYILAN alanlar (is_engineering=true):
- Yazılım / bilişim mühendisliği, bilgisayar mühendisliği
- Elektrik-elektronik mühendisliği
- Makine mühendisliği
- Havacılık ve uzay mühendisliği
- İnşaat mühendisliği
- Endüstri mühendisliği
- Mekatronik mühendisliği
- Biyomedikal mühendisliği
- Savunma sanayi AR-GE
- Robotik
- Gömülü sistem / donanım geliştirme

MÜHENDİSLİK SAYILMAYAN alanlar (is_engineering=false):
- Saf pazarlama, tanıtım, reklam, halkla ilişkiler
- Gıda üretimi/satışı (mühendislik AR-GE'si olmayan)
- Genel danışmanlık (yönetim, hukuk, finans danışmanlığı - teknik AR-GE değilse)
- Genel ticaret/toptan-perakende satış
- Turizm, eğitim (teknik mühendislik eğitimi/AR-GE'si değilse)

ÖNEMLİ ÖRNEK: "ZUPPA ELEKTRONİK İLETİŞİM TANITIM PAZARLAMA GIDA SANAYİ VE TİCARET ANONİM ŞİRKETİ"
İsminde "ELEKTRONİK" geçse de bu firma esasen tanıtım/pazarlama/gıda/ticaret firmasıdır.
Bu tarz firmalar is_engineering=false olarak işaretlenmelidir. İsimde geçen tek bir mühendislik
kelimesi yeterli değildir; firmanın asıl faaliyet alanına (isim + sektör etiketi) bakarak karar ver.

ÜNİVERSİTE/AKADEMİK/KAMU İSTİSNASI: Üniversite, enstitü, araştırma merkezi, kamu kurumu, TÜBİTAK
gibi kurumsal/akademik birimler MÜHENDİSLİK OLARAK SAYILMAZ, is_engineering=false olmalıdır
(firma adında "ÜNİVERSİTESİ", "ENSTİTÜSÜ", "ARAŞTIRMA MERKEZİ" gibi ifadeler geçiyorsa özellikle
dikkat et). Bu durumda reason alanına "üniversite/akademik birim, şirket değil" yaz. Bu iş başvurusu
kampanyası ticari şirketleri hedefler; akademik/kamu birimleri hedef değildir.

Sana bir firma listesi (isim ve varsa sektör etiketi) verilecek. Her firma için karar ver.

Yanıtını SADECE şu JSON formatında ver:
{"results": [{"name": "...", "is_engineering": true/false, "reason": "kısa gerekçe (max 15 kelime)"}, ...]}

Listedeki TÜM firmalar için, aynı sırayla, bir sonuç döndür.
"""


def load_companies() -> list[dict]:
    with INPUT_PATH.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def classify_batch(client: OpenAI, batch: list[dict]) -> list[dict]:
    user_content = json.dumps(
        [{"name": c["name"], "sector": c.get("sector", "")} for c in batch],
        ensure_ascii=False,
    )
    resp = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    return data.get("results", [])


def main() -> None:
    companies = load_companies()
    if not companies:
        print("companies_raw.csv bos veya bulunamadi. Once 1_scrape_companies.py calistirin.")
        return

    client = OpenAI()
    filtered = []

    for i in range(0, len(companies), BATCH_SIZE):
        batch = companies[i : i + BATCH_SIZE]
        print(f"[classify] {i + 1}-{i + len(batch)} / {len(companies)}...")
        try:
            results = classify_batch(client, batch)
        except Exception as exc:  # noqa: BLE001
            print(f"  hata: {exc}")
            continue

        results_by_name = {r.get("name", "").strip().lower(): r for r in results}
        for company in batch:
            key = company["name"].strip().lower()
            result = results_by_name.get(key)
            if not result:
                continue

            is_engineering = bool(result.get("is_engineering"))
            reason = result.get("reason", "")

            if is_academic_institution(company["name"]):
                is_engineering = False
                reason = "üniversite/akademik birim, şirket değil"

            if is_engineering:
                filtered.append(
                    {
                        "name": company["name"],
                        "sector": company.get("sector", ""),
                        "is_engineering": True,
                        "reason": reason,
                    }
                )

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "sector", "is_engineering", "reason"])
        writer.writeheader()
        writer.writerows(filtered)

    print(f"\n{len(filtered)} / {len(companies)} firma muhendislik olarak isaretlendi -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
