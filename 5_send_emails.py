"""companies_emails.csv icindeki mailleri Gmail API (OAuth2) ile CV eki ile
gonderir ve sonucu bir Excel dosyasina loglar.

Ilk calistirmada tarayici acilir, Google hesabinla giris yapip izin verirsin,
token token.json dosyasina kaydedilir ve sonraki calistirmalarda tekrar
sorulmaz. credentials.json dosyasi bu klasorde olmali (Google Cloud Console'dan
indirilen OAuth "Desktop app" client secret dosyasi).

CV_PATH .env'den okunur ve proje klasorune (bu dosyanin bulundugu klasore)
gore relative bir yoldur. Dosya adinda bosluk olsa bile oldugu gibi yazilabilir
(tirnak gerekmez), cunku python-dotenv satirin tamamini deger olarak okur.

Cikti: data/companies_sent_log.xlsx (name, email, subject, status, detail, timestamp, CV Eklendi)
"""
import base64
import mimetypes
import time
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from common import BASE_DIR, DATA_DIR, env, env_float

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"

INPUT_PATH = DATA_DIR / "companies_emails.csv"
LOG_PATH = DATA_DIR / "companies_sent_log.xlsx"

GMAIL_SENDER = env("GMAIL_SENDER", "")
SEND_DELAY = env_float("SEND_DELAY", 2.0)
DRY_RUN = env("DRY_RUN", "true").strip().lower() in ("1", "true", "yes")

CV_PATH_RAW = env("CV_PATH", "")
CV_PATH = (BASE_DIR / CV_PATH_RAW).resolve() if CV_PATH_RAW else None


def get_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"credentials.json bulunamadi: {CREDENTIALS_PATH}\n"
                    "Google Cloud Console'dan 'OAuth client ID -> Desktop app' olusturup "
                    "indirdigin dosyayi bu isimle bu klasore koy."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


def build_message(to_email: str, subject: str, body: str) -> dict:
    message = MIMEMultipart()
    message["to"] = to_email
    message["subject"] = subject
    if GMAIL_SENDER:
        message["from"] = GMAIL_SENDER

    message.attach(MIMEText(body, "plain", "utf-8"))

    cv_bytes = CV_PATH.read_bytes()
    ctype, _ = mimetypes.guess_type(CV_PATH.name)
    if ctype != "application/pdf":
        ctype = "application/pdf"
    main_type, sub_type = ctype.split("/", 1)
    attachment = MIMEBase(main_type, sub_type)
    attachment.set_payload(cv_bytes)
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition", "attachment", filename=CV_PATH.name
    )
    message.attach(attachment)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw}


def main() -> None:
    if not CV_PATH:
        raise SystemExit(
            "CV dosyasi bulunamadi: .env dosyasinda CV_PATH bos. "
            "Lutfen .env'e CV_PATH=<proje klasorune gore relative dosya yolu> ekleyin."
        )
    if not CV_PATH.exists():
        raise SystemExit(f"CV dosyasi bulunamadi: {CV_PATH}, .env'deki CV_PATH'i kontrol edin")

    df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
    if df.empty:
        print("companies_emails.csv bos. Once 4_generate_emails.py calistirin.")
        return

    if DRY_RUN:
        print("DRY_RUN=true : gercek mail GONDERILMEYECEK, sadece loglanacak.")
    print(f"CV eki: {CV_PATH}")

    service = None
    if not DRY_RUN:
        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)

    log_rows = []
    for idx, row in df.iterrows():
        name = row["name"]
        to_email = row["email"]
        subject = row["subject"]
        body = row["body"]
        print(f"[send] {idx + 1}/{len(df)}: {name} <{to_email}>")

        status = "error"
        detail = ""
        cv_attached = False

        if DRY_RUN:
            status = "dry_run"
            detail = "gonderilmedi (DRY_RUN=true)"
            cv_attached = True
        else:
            try:
                message = build_message(to_email, subject, body)
                cv_attached = True
                sent = service.users().messages().send(userId="me", body=message).execute()
                status = "sent"
                detail = sent.get("id", "")
            except HttpError as exc:
                status = "error"
                detail = str(exc)
            except Exception as exc:  # noqa: BLE001
                status = "error"
                detail = str(exc)

            time.sleep(SEND_DELAY)

        log_rows.append(
            {
                "name": name,
                "email": to_email,
                "subject": subject,
                "status": status,
                "detail": detail,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "CV Eklendi": "Evet" if cv_attached else "Hayır",
            }
        )

    log_df = pd.DataFrame(log_rows)
    log_df.to_excel(LOG_PATH, index=False)

    sent_count = sum(1 for r in log_rows if r["status"] == "sent")
    print(f"\n{sent_count} / {len(log_rows)} mail gonderildi -> {LOG_PATH}")


if __name__ == "__main__":
    main()
