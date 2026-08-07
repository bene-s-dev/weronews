import os
import re
import html
import time
from urllib.parse import parse_qs, urlparse
import feedparser
from supabase import create_client, Client

# Supabase Konfiguration (nutzt Umgebungsvariablen für GitHub Actions oder deine Direkt-Keys als Fallback)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jyoxxkngxxfmiskfxndp.supabase.co")
SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_KEY", 
    os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5b3h4a25neHhmbWlza2Z4bmRwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU5Mjg4NTQsImV4cCI6MjEwMTUwNDg1NH0.g6iDSYtD9rCU8SMKdpqg8OTIK8VYueYbbXvQe2ouwXg")
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Deine Google Alert RSS Feed-URL
RSS_URL = "https://www.google.com/alerts/feeds/04501937703243340539/10721502900236254242"
RSS_FEEDS = [RSS_URL]

def clean_google_link(raw_url: str) -> str:
    """Extrahiert die echte Ziel-URL aus Google-Alert- & Tracking-Weiterleitungen."""
    if not raw_url:
        return ""
    
    parsed = urlparse(raw_url)
    if "google.com" in parsed.netloc:
        query_params = parse_qs(parsed.query)
        # Google Alert Weiterleitungen nutzen meist 'url' oder 'q' als Parameter
        if "url" in query_params and query_params["url"]:
            return query_params["url"][0]
        if "q" in query_params and query_params["q"]:
            return query_params["q"][0]
            
    return raw_url

def clean_text(text: str) -> str:
    """Dekodiert HTML-Entities (&amp;, &quot;) und entfernt HTML-Tags (z.B. <b>Wero</b>)."""
    if not text:
        return ""
    # Erst HTML-Entities auflösen (&amp; -> &)
    decoded = html.unescape(text)
    # Alle HTML-Tags entfernen
    cleaned = re.sub(r'<[^>]+?>', '', decoded)
    return cleaned.strip()

def parse_pub_date(entry) -> str:
    """Konvertiert das Feed-Datum sicher in ein ISO-8601 Format für Supabase."""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', entry.published_parsed)
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', entry.updated_parsed)
    # Fallback auf ISO-Format für Jetzt
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def fetch_and_sync_news():
    print("🚀 Starte RSS Feed Abruf...")
    articles_to_upsert = []
    seen_links = set()

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            print(f"📡 Feed geladen ({len(feed.entries)} Einträge gefunden): {feed_url[:50]}...")

            for entry in feed.entries:
                raw_link = getattr(entry, "link", "")
                clean_link = clean_google_link(raw_link)
                title = clean_text(getattr(entry, "title", ""))

                # Wenn Link oder Titel fehlen oder der Link bereits verarbeitet wurde, überspringen
                if not clean_link or not title or clean_link in seen_links:
                    continue

                seen_links.add(clean_link)

                # Quellennamen bestimmen
                author = getattr(entry, "author", "")
                source_dict = getattr(entry, "source", {})
                source_title = source_dict.get("title", "") if isinstance(source_dict, dict) else ""
                
                source = clean_text(author or source_title)
                if not source or source.lower() in ["google alert", "none"]:
                    # Domain als Fallback-Quelle nutzen
                    domain = urlparse(clean_link).netloc.replace("www.", "")
                    source = domain if domain else "Google Alert"

                pub_date = parse_pub_date(entry)

                articles_to_upsert.append({
                    "title": title,
                    "link": clean_link,
                    "source": source,
                    "pub_date": pub_date
                })

        except Exception as e:
            print(f"⚠️ Fehler beim Verarbeiten des Feeds {feed_url}: {e}")

    if articles_to_upsert:
        print(f"📦 Sende {len(articles_to_upsert)} bereinigte Artikel an Supabase...")
        try:
            # on_conflict="link" verhindert Duplikate basierend auf der eindeutigen URL
            response = supabase.table("news").upsert(articles_to_upsert, on_conflict="link").execute()
            print("✅ Erfolgreich synchronisiert!")
        except Exception as e:
            print(f"⚠️ Batch-Upsert fehlgeschlagen: {e}. Versuche Einzel-Übertragung...")
            # Fallback: Einzelne Artikel hochladen, falls ein bestimmter Eintrag fehlerhaft ist
            saved_count = 0
            for article in articles_to_upsert:
                try:
                    supabase.table("news").upsert(article, on_conflict="link").execute()
                    saved_count += 1
                except Exception as single_err:
                    print(f"❌ Fehler bei Artikel '{article.get('title')}': {single_err}")
            print(f"✅ Synchronisation abgeschlossen: {saved_count}/{len(articles_to_upsert)} gespeichert.")
    else:
        print("ℹ️ Keine neuen Artikel zum Speichern gefunden.")

if __name__ == "__main__":
    fetch_and_sync_news()
