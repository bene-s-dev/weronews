import feedparser
from googlenewsdecoder import gnd
from supabase import create_client

SUPABASE_URL = "https://jyoxxkngxxfmiskfxndp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5b3h4a25neHhmbWlza2Z4bmRwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU5Mjg4NTQsImV4cCI6MjEwMTUwNDg1NH0.g6iDSYtD9rCU8SMKdpqg8OTIK8VYueYbbXvQe2ouwXg"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

query = 'Wero OR "Martina Weimert" OR "EPI Company"'
rss_url = f'https://news.google.com/rss/search?q={query}&hl=de&gl=DE&ceid=DE:de'

feed = feedparser.parse(rss_url)

for entry in feed.entries[:15]:
    try:
        decoded_url = gnd(entry.link)
        clean_url = decoded_url.get("decoded_url", entry.link)
        
        title = entry.title
        source = entry.source.title if hasattr(entry, 'source') else "Google News"

        supabase.table("news").upsert({
            "title": title,
            "link": clean_url,
            "source": source,
            "pub_date": entry.published
        }, on_conflict="link").execute()

    except Exception as e:
        print(f"Fehler bei Eintrag: {e}")

print("Sync erfolgreich!")
