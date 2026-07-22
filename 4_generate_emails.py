"""companies_contacts.csv icinde status=found olan firmalar icin OpenAI ile
kisisellestirilmis Turkce IS BASVURUSU maili (konu + govde) uretir.

Cikti: data/companies_emails.csv (name, sector, website, email, subject, body)
"""
import csv
import json

from openai import OpenAI

from common import DATA_DIR, env

INPUT_PATH = DATA_DIR / "companies_contacts.csv"
OUTPUT_PATH = DATA_DIR / "companies_emails.csv"

MODEL = env("OPENAI_MODEL", "gpt-4o-mini")

SENDER_NAME = env("SENDER_NAME", "")
SENDER_TITLE = env("SENDER_TITLE", "")
SENDER_COMPANY = env("SENDER_COMPANY", "")
EMAIL_PURPOSE = env("EMAIL_PURPOSE", "")

SYSTEM_PROMPT = """Sen bir iş arayan aday adına Türkçe İŞ BAŞVURUSU e-postaları yazan bir asistansın.
Bu bir satış, tanıtım veya iş birliği teklifi maili DEĞİLDİR — açık ve dürüst bir iş başvurusu mailidir.

Ton: mütevazı, profesyonel, kendine güvenen ama gösterişsiz bir iş arayan adayın sesi. Abartılı
övünme, agresif satış dili veya "harika bir fırsat sunuyorum" tarzı pazarlama üslubundan kaçın.

İçerik kuralları:
- Mail "Sayın {Firma Adı} Yetkilisi," gibi kibar bir hitapla başlasın.
- Firma adına ve (varsa) sektörüne doğal bir şekilde referans ver; şablon/kopya-yapıştır hissi
  vermesin, her mail o firmaya özel yazılmış gibi okunmalı.
- Adayın kim olduğunu, hangi pozisyon/alanda çalışmak istediğini (aday profili) kısaca belirt.
- Mail ekinde özgeçmiş (CV) olduğunu doğal bir cümleyle belirt (örn. "Ekte özgeçmişimi
  bulabilirsiniz.").
- Sonunda net ve kibar bir call-to-action olsun: kısa bir görüşme veya mülakat talebi.
- Toplam uzunluk 100-150 kelime olsun, gereksiz uzatma.
- Saygılı bir kapanış ve imza ile bitir.

Yanıtını SADECE şu JSON formatında ver:
{"subject": "...", "body": "..."}

body alanında paragraflar arasında \\n\\n kullan. Selamlama ve imza dahil et.
"""


def build_user_prompt(company: dict) -> str:
    return json.dumps(
        {
            "firma_adi": company["name"],
            "sektor": company.get("sector", ""),
            "gonderen_adi": SENDER_NAME,
            "basvurulan_pozisyon_veya_aday_profili": SENDER_TITLE,
            "gonderen_sirketi_varsa": SENDER_COMPANY,
            "basvuru_amaci_ek_not": EMAIL_PURPOSE,
        },
        ensure_ascii=False,
    )


def main() -> None:
    if not EMAIL_PURPOSE.strip():
        print(
            "UYARI: .env dosyasinda EMAIL_PURPOSE bos. Mailin amacini belirtmezseniz "
            "cikti genel/belirsiz olabilir. Yine de devam ediliyor..."
        )

    with INPUT_PATH.open(encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("status") == "found" and r.get("email")]

    if not rows:
        print("Gonderilecek 'found' statusunde firma yok. Once 3_find_contacts.py calistirin.")
        return

    client = OpenAI()
    results = []

    for idx, company in enumerate(rows, start=1):
        print(f"[emails] {idx}/{len(rows)}: {company['name']}")
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(company)},
                ],
                temperature=0.7,
            )
            data = json.loads(resp.choices[0].message.content)
            subject = data.get("subject", "").strip()
            body = data.get("body", "").strip()
        except Exception as exc:  # noqa: BLE001
            print(f"  hata: {exc}")
            continue

        if not subject or not body:
            continue

        results.append(
            {
                "name": company["name"],
                "sector": company.get("sector", ""),
                "website": company.get("website", ""),
                "email": company["email"],
                "subject": subject,
                "body": body,
            }
        )

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "sector", "website", "email", "subject", "body"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{len(results)} mail uretildi -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
