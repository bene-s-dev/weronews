import email.utils
from datetime import datetime, timezone
import requests
import feedparser

# Google News RSS Feed für "wero"
RSS_URL = "https://news.google.com/rss/search?q=wero&hl=de&gl=DE&ceid=DE:de"

# Supabase API Settings
SUPABASE_URL = "https://jyoxxkngxxfmiskfxndp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5b3h4a25neHhmbWlza2Z4bmRwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU5Mjg4NTQsImV4cCI6MjEwMTUwNDg1NH0.g6iDSYtD9rCU8SMKdpqg8OTIK8VYueYbbXvQe2ouwXg"


def parse_pub_date(published_str):
    """
    Parst den RSS pubDate String in das ISO 8601 Format für Supabase.
    """
    if not published_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = email.utils.parsedate_to_datetime(published_str)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def resolve_final_url(google_url):
    """
    Versucht den Google News Redirect aufzulösen, um die echte Ziel-URL zu erhalten.
    """
    try:
        response = requests.head(google_url, allow_redirects=True, timeout=3)
        return response.url
    except Exception:
        return google_url


def fetch_and_sync_news():
    print("🚀 Starte Google News RSS Abruf...")
    feed = feedparser.parse(RSS_URL)

    if not feed.entries:
        print("⚠️ Keine Einträge im Google News Feed gefunden.")
        return

    print(f"📡 Feed geladen ({len(feed.entries)} Einträge gefunden).")

    articles_to_upsert = []

    for entry in feed.entries:
        title = entry.get("title", "").strip()
        raw_link = entry.get("link", "").strip()

        if not title or not raw_link:
            continue

        pub_date = parse_pub_date(entry.get("published", ""))
        description = entry.get("summary", "") or entry.get("description", "")
        final_link = resolve_final_url(raw_link)

        article_payload = {
            "title": title,
            "link": final_link,
            "pub_date": pub_date,
            "description": description,
        }

        articles_to_upsert.append(article_payload)

    print(f"📦 Sende {len(articles_to_upsert)} Artikel an Supabase...")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    supabase_endpoint = f"{SUPABASE_URL}/rest/v1/news?on_conflict=link"

    try:
        res = requests.post(
            supabase_endpoint, headers=headers, json=articles_to_upsert, timeout=10
        )
        if res.status_code in (200, 201):
            print(
                f"✅ Synchronisation erfolgreich! {len(articles_to_upsert)} Artikel verarbeitet."
            )
        else:
            print(f"❌ Fehler bei Supabase Upsert ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"❌ Netzwerkfehler bei der Übertragung: {e}")


if __name__ == "__main__":
    fetch_and_sync_news()
