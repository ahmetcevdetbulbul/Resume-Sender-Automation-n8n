# Cyberpark Outreach — Python İş Başvurusu Otomasyonu

n8n veya başka bir low-code araç kullanmadan, tamamen **Python** ile yazılmış
uçtan uca bir iş başvurusu outreach pipeline'ı. [Cyberpark](https://www.cyberpark.com.tr/)
firma arşivini tarar, mühendislik alanında faaliyet gösteren ticari şirketleri
tespit eder, her biri için resmi web sitesini ve iletişim e-postasını bulur,
OpenAI ile kişiselleştirilmiş bir iş başvurusu maili yazdırır ve CV ekiyle
birlikte Gmail üzerinden gönderir.

Her adım bağımsız bir script olarak çalışır, kendi CSV/Excel çıktısını üretir
ve istenildiği zaman tek başına tekrar çalıştırılabilir.

## Pipeline

| # | Script | Görev | Çıktı |
|---|--------|-------|-------|
| 1 | `1_scrape_companies.py` | Firma arşivi sayfalarını (Playwright) tarar, firma adı + sektör bilgisini toplar | `data/companies_raw.csv` |
| 2 | `2_classify_engineering.py` | OpenAI ile firmaları mühendislik/değil diye sınıflandırır, akademik/kamu kurumlarını eler | `data/companies_filtered.csv` |
| 3 | `3_find_contacts.py` | Bing araması + domain tahmini ile web sitesini bulur, e-postayı çıkarır, bulunan sitenin doğru firmaya ait olduğunu doğrular | `data/companies_contacts.csv` |
| 4 | `4_generate_emails.py` | OpenAI ile kişiye özel, Türkçe bir iş başvurusu maili (konu + gövde) üretir | `data/companies_emails.csv` |
| 5 | `5_send_emails.py` | Gmail API (OAuth2) ile CV ekli maili gönderir, sonucu Excel'e loglar | `data/companies_sent_log.xlsx` |

```bash
python 1_scrape_companies.py
python 2_classify_engineering.py
python 3_find_contacts.py
python 4_generate_emails.py
python 5_send_emails.py
```

## Öne çıkan tasarım kararları

- **Playwright tabanlı tarama** — hem Cyberpark sitesi hem arama motorları
  headless Chromium ile ziyaret edilir; düz `requests` isteklerinin
  engellendiği durumlar için bu tercih edildi.
- **İki katmanlı website bulma** — önce Bing araması, sonuç yoksa firma
  adından türetilen marka adıyla (`{marka}.com.tr`, `{marka}.com` vb.) olası
  domainler doğrudan denenir.
- **Otomatik doğrulama** — bulunan sitenin gerçekten aranan firmaya ait olup
  olmadığı, firma adından çıkarılan marka kelimesinin site içeriğinde geçip
  geçmediğine bakılarak kontrol edilir (`status=mismatch` ile işaretlenir).
- **Güvenli varsayılanlar** — gönderim adımı varsayılan olarak `DRY_RUN=true`
  ile çalışır; gerçek e-posta göndermeden önce üretilen içerikleri gözden
  geçirmeyi zorunlu kılar.
- **Türkçe karakter duyarlılığı** — sınıflandırma ve marka eşleştirme
  adımlarında Türkçe büyük/küçük harf dönüşümü (`İ`/`I`/`ı`) özel olarak ele
  alınır.

## Kurulum

```bash
pip install -r requirements.txt
playwright install chromium
```

`.env.example` dosyasını `.env` olarak kopyalayıp doldur:

```bash
copy .env.example .env
```

| Değişken | Açıklama |
|---|---|
| `OPENAI_API_KEY` | OpenAI API anahtarı |
| `OPENAI_MODEL` | Varsayılan `gpt-4o-mini` |
| `SENDER_NAME` | Ad soyad |
| `SENDER_TITLE` | Başvurulan pozisyon / aday profili (ör. `Yazılım Mühendisi / Bilgisayar Mühendisliği mezunu`) |
| `EMAIL_PURPOSE` | Maile ek bağlam; boş bırakılmamalı |
| `GMAIL_SENDER` | Gönderen Gmail adresi |
| `CV_PATH` | Gönderilecek CV/PDF dosyasının proje klasörüne göre relative yolu |
| `DRY_RUN` | `true` iken gerçek mail göndermez, sadece loglar (varsayılan) |
| `REQUEST_DELAY` | İstekler arası bekleme süresi (saniye) |

`CV_PATH` dosya adında boşluk olsa bile tırnak kullanmadan olduğu gibi
yazılır (`.env` satırının tamamı değer olarak okunur), örn:

```
CV_PATH=Ad Soyad CV.pdf
```

`5_send_emails.py` başlarken bu dosyanın var olup olmadığını kontrol eder;
bulunamazsa (DRY_RUN modunda bile) açık bir hata mesajıyla erken durur.

### Gmail OAuth2 kurulumu

1. Google Cloud Console'da bir proje oluştur, Gmail API'yi etkinleştir.
2. OAuth Client ID → **Desktop app** oluştur, indirilen dosyayı proje
   klasörüne `credentials.json` olarak koy.
3. İlk çalıştırmada tarayıcı açılıp giriş isteyecek; onay sonrası `token.json`
   kaydedilir ve sonraki çalıştırmalarda tekrar sorulmaz.

`credentials.json`, `token.json` ve `.env` `.gitignore` ile repoya dahil
edilmez.

## Proje yapısı

```
cyberpark-outreach/
├── common.py                   # ortak env/yardımcı fonksiyonlar
├── 1_scrape_companies.py
├── 2_classify_engineering.py
├── 3_find_contacts.py
├── 4_generate_emails.py
├── 5_send_emails.py
├── debug_search.py              # Bing arama + domain tahmini için debug aracı
├── requirements.txt
├── .env.example
└── data/                        # her adımın ürettiği CSV/Excel çıktıları (gitignore'da)
```

## Notlar

- `REQUEST_DELAY` scraping/arama istekleri arası bekleme süresini belirler;
  rate-limit'e takılırsan artır.
- Her script bağımsız çalıştırılabilir; bir adımı tekrar çalıştırmak
  sonraki adımların girdisini bozmaz.
- Adım 5'i gerçek gönderim için çalıştırmadan önce `DRY_RUN=false` yap ve
  `data/companies_emails.csv`'yi mutlaka gözden geçir.

## Sorumlu kullanım

Bu araç, halka açık bir firma dizinindeki bilgilerden yola çıkarak kişisel
iş başvurusu amaçlı iletişim kurmak için tasarlanmıştır. Toplu/istenmeyen
pazarlama amacıyla kullanılması önerilmez; hedef sitelerin `robots.txt` ve
kullanım şartlarına, ayrıca ilgili KVKK/GDPR yükümlülüklerine dikkat edilmelidir.
