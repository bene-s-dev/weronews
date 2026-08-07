import feedparser
import re
from urllib.parse import parse_qs, urlparse
from supabase import create_client

SUPABASE_URL = "https://jyoxxkngxxfmiskfxndp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5b3h4a25neHhmbWlza2Z4bmRwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU5Mjg4NTQsImV4cCI6MjEwMTUwNDg1NH0.g6iDSYtD9rCU8SMKdpqg8OTIK8VYueYbbXvQe2ouwXg"  # Hier deinen echten Supabase Key eintragen!

# Deine Google Alert RSS Feed-URL:
RSS_URL = "https://www.google.com/alerts/feeds/04501937703243340539/10721502900236254242"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def clean_google_link(raw_url):
    """Extrahiert den echten Zeitungs-Link aus dem Google-Tracking-Link."""
    parsed = urlparse(raw_url)
    if "google.com" in parsed.netloc:
        query_params = parse_qs(parsed.query)
        if "url" in query_params:
            return query_params["url"][0]
    return raw_url

def clean_html_tags(text):
    """Entfernt HTML-Tags wie <b>Wero</b> aus den Titeln."""
    return re.sub('<[^<]+?>', '', text)

feed = feedparser.parse(RSS_URL)

for entry in feed.entries:
    try:
        title = clean_html_tags(entry.title)
        clean_link = clean_google_link(entry.link)
        
        # Falls eine Quelle angegeben ist, sonst Standard setzen
        source = entry.author if hasattr(entry, 'author') and entry.author else "Google Alert"

        supabase.table("news").upsert({
            "title": title,
            "link": clean_link,
            "source": source,
            "pub_date": entry.published
        }, on_conflict="link").execute()

    except Exception as e:
        print(f"Fehler bei Eintrag: {e}")

print("Sync via RSS-Feed erfolgreich!")
