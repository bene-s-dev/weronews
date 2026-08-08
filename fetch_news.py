import email.utils
import html
import re
import urllib.parse
from datetime import datetime, timezone
import feedparser
import requests

# Deine originale Google Alerts RSS Feed URL
ALERTS_URL = "https://www.google.de/alerts/feeds/04501937703243340539/10721502900236254242"

# Supabase API Konfiguration
SUPABASE_URL = "https://jyoxxkngxxfmiskfxndp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5b3h4a25neHhmbWlza2Z4bmRwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU5Mjg4NTQsImV4cCI6MjEwMTUwNDg1NH0.g6iDSYtD9rCU8SMKdpqg8OTIK8VYueYbbXvQe2ouwXg"


def clean_text(text):
    """Entfernt HTML-Tags (wie <b>wero</b>) und wandelt HTML-Entities um."""
    if not text:
        return ""
    text_without_html = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text_without_html).strip()


def extract_real_url(google_url):
    """Extrahiert die echte Ziel-URL aus dem Google-Weiterleitungs-Link."""
    if not google_url:
        return ""
    try:
        parsed = urllib.parse.urlparse(google_url)
        query = urllib.parse.parse_qs(parsed.query)
        if "url" in query and query["url"]:
            return query["url"][0]
    except Exception:
        pass
    return google_url


def parse_pub_date(published_str):
    """Parst das Veröffentlichungsdatum in ISO 8601 für Supabase."""
    if not published_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = email.utils.parsedate_to_datetime(published_str)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def fetch_and_sync_news():
    print("🚀 Starte Google Alerts RSS Abruf...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(ALERTS_URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Fehler beim Abrufen des Google Alerts Feeds: {e}")
        return

    feed = feedparser.parse(response.content)

    if not feed.entries:
        print("⚠️ Keine Einträge im Google Alerts Feed gefunden.")
        return

    print(f"📡 Feed geladen ({len(feed.entries)} Einträge gefunden).")

    articles_to_upsert = []

    for entry in feed.entries:
        raw_title = entry.get("title", "")
        raw_link = entry.get("link", "")

        if not raw_title or not raw_link:
            continue

        clean_title = clean_text(raw_title)
        real_link = extract_real_url(raw_link)
        pub_date = parse_pub_date(entry.get("published", "") or entry.get("updated", ""))
        raw_desc = entry.get("summary", "") or entry.get("description", "")
        clean_desc = clean_text(raw_desc)

        # Nur gültige Tabellenspalten (ohne 'summary')
        article_payload = {
            "title": clean_title,
            "link": real_link,
            "pub_date": pub_date,
            "description": clean_desc,
        }

        articles_to_upsert.append(article_payload)

    if not articles_to_upsert:
        print("⚠️ Keine gültigen Artikel zum Hochladen gefunden.")
        return

    print(f"📦 Sende {len(articles_to_upsert)} Artikel an Supabase...")

    supabase_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    supabase_endpoint = f"{SUPABASE_URL}/rest/v1/news?on_conflict=link"

    try:
        res = requests.post(
            supabase_endpoint, headers=supabase_headers, json=articles_to_upsert, timeout=15
        )
        if res.status_code in (200, 201):
            print(f"✅ Synchronisation erfolgreich! {len(articles_to_upsert)} Artikel verarbeitet.")
        else:
            print(f"❌ Fehler bei Supabase Upsert ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"❌ Netzwerkfehler bei der Übertragung an Supabase: {e}")


if __name__ == "__main__":
    fetch_and_sync_news()
