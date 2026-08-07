import feedparser
import urllib.parse
from supabase import create_client

SUPABASE_URL = "https://jyoxxkngxxfmiskfxndp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5b3h4a25neHhmbWlza2Z4bmRwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU5Mjg4NTQsImV4cCI6MjEwMTUwNDg1NH0.g6iDSYtD9rCU8SMKdpqg8OTIK8VYueYbbXvQe2ouwXg"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

raw_query = 'Wero OR "Martina Weimert" OR "EPI Company"'
query = urllib.parse.quote(raw_query)
rss_url = f'https://news.google.com/rss/search?q={query}&hl=de&gl=DE&ceid=DE:de'

feed = feedparser.parse(rss_url)

for entry in feed.entries[:15]:
    try:
        title = entry.title
        source = entry.source.title if hasattr(entry, 'source') else "Google News"
        clean_url = entry.link

        supabase.table("news").upsert({
            "title": title,
            "link": clean_url,
            "source": source,
            "pub_date": entry.published
        }, on_conflict="link").execute()

    except Exception as e:
        print(f"Fehler bei Eintrag: {e}")

print("Sync erfolgreich!")
