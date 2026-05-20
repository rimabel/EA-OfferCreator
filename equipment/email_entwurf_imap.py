#!/usr/bin/env python3
"""
Equipment: email_entwurf_imap.py
Zweck: E-Mail-Entwurf mit PDF-Anhang via IMAP in den Drafts-Ordner speichern.
Konfiguration: wird vollständig aus .env Datei geladen
"""

import imaplib
import os
import sys
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formatdate
from datetime import datetime, timezone


def load_env(env_path=".env"):
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('\'"'))
    except FileNotFoundError:
        print(f"❌ Fehler: .env Datei nicht gefunden unter '{env_path}'")
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="E-Mail-Entwurf mit PDF-Anhang via IMAP speichern.")
    parser.add_argument("--an",         required=True, help="Empfänger-E-Mail")
    parser.add_argument("--betreff",    required=True, help="E-Mail-Betreff")
    parser.add_argument("--text",       required=True, help="Pfad zur .txt Datei mit dem E-Mail-Text")
    parser.add_argument("--pdf",        required=True, help="Pfad zur PDF-Datei als Anhang")
    parser.add_argument("--angebotsnr", required=True, help="Angebotsnummer (für Dateiname)")
    parser.add_argument("--env",        default=".env", help="Pfad zur .env Datei (Standard: .env)")
    return parser.parse_args()


def build_email(args, imap_user):
    msg = MIMEMultipart()
    msg["From"]    = f"Nabil Belahmer <{imap_user}>"
    msg["To"]      = args.an
    msg["Subject"] = args.betreff
    msg["Date"]    = formatdate(localtime=True)

    with open(args.text, "r", encoding="utf-8") as f:
        body = f.read()
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with open(args.pdf, "rb") as f:
        pdf_data = f.read()
    attachment = MIMEApplication(pdf_data, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=f"{args.angebotsnr}.pdf")
    msg.attach(attachment)

    return msg


def save_draft(msg):
    host          = os.environ.get("IMAP_HOST", "")
    port          = int(os.environ.get("IMAP_PORT", "143"))
    user          = os.environ.get("IMAP_USER", "")
    drafts_folder = os.environ.get("IMAP_DRAFTS_FOLDER", "Drafts")
    password      = os.environ.get("IMAP_PASSWORD", "")

    for var, val in [("IMAP_HOST", host), ("IMAP_USER", user), ("IMAP_PASSWORD", password)]:
        if not val:
            print(f"❌ Fehler: {var} nicht in .env gefunden.")
            sys.exit(1)

    mail = imaplib.IMAP4(host, port)
    try:
        mail.starttls()
        mail.login(user, password)

        try:
            mail.select(drafts_folder)
        except imaplib.IMAP4.error:
            mail.create(drafts_folder)
            mail.select(drafts_folder)

        result = mail.append(
            drafts_folder,
            "\\Draft",
            imaplib.Time2Internaldate(datetime.now(timezone.utc)),
            msg.as_bytes()
        )

        if result[0] == "OK":
            print(f"✅ Entwurf erfolgreich gespeichert in '{drafts_folder}'.")
        else:
            print(f"⚠️ Unerwartetes Ergebnis: {result}")

    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP-Fehler: {e}")
        sys.exit(1)
    finally:
        mail.logout()


if __name__ == "__main__":
    args = parse_args()
    load_env(args.env)
    imap_user = os.environ.get("IMAP_USER", "")
    print(f"📧 Erstelle Entwurf für: {args.an}")
    print(f"   Betreff:  {args.betreff}")
    print(f"   PDF:      {args.pdf}")
    msg = build_email(args, imap_user)
    save_draft(msg)
