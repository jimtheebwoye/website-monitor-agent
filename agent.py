import feedparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import time
import re
import json
import requests
from newspaper import Article  # pip install newspaper3k

# =====================
# CONFIG
# =====================
RSS_FEEDS = [
    "https://www.theregister.com/headlines.atom",
    "https://www.theregister.com/security/headlines.atom",
    "https://computerweekly.com/rss/All-Computerweekly.xml",
    "https://cio.com/feed"
]

KEYWORDS = ["SAP", "HMRC", "BTP", "S/4HANA", "Sovereign"]

EMAIL_FROM = "jimtheebwoye@gmail.com"
EMAIL_TO = "jimtheebwoye@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

STATE_FILE = "sent_articles.json"

# Hugging Face summarisation model
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")
HF_MODEL_URL = "https://api-inference.huggingface.co/models/sshleifer/distilbart-cnn-12-6"

# =====================
# STATE (DEDUPLICATION)
# =====================
def load_sent_articles():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_sent_articles(urls):
    with open(STATE_FILE, "w") as f:
        json.dump(list(urls), f)

# =====================
# KEYWORD MATCHING
# =====================
def get_matching_keywords(text):
    matches = []
    text_lower = text.lower()
    for keyword in KEYWORDS:
        if keyword == "SAP":
            if re.search(r"\bSAP\b", text, re.IGNORECASE):
                matches.append(keyword)
        else:
            if keyword.lower() in text_lower:
                matches.append(keyword)
    return matches

# =====================
# FETCH FULL ARTICLE TEXT
# =====================
def fetch_full_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"Failed to fetch article text from {url}: {e}")
        return ""

# =====================
# HUGGING FACE SUMMARY
# =====================
def summarize_text(text, retries=2):
    if not HF_API_KEY or not text.strip():
        return "Summary unavailable (no text or API key missing)."

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": text[:2500],
        "parameters": {
            "max_length": 250,
            "min_length": 120,
            "do_sample": False
        }
    }

    try:
        response = requests.post(
            HF_MODEL_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code in (429, 503) and retries > 0:
            print("Hugging Face busy. Retrying in 20 seconds...")
            time.sleep(20)
            return summarize_text(text, retries - 1)

        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and "summary_text" in data[0]:
            return data[0]["summary_text"]

        return "Summary unavailable."
    except Exception as e:
        print(f"Summarisation failed: {e}")
        return "Summary unavailable."

# =====================
# FETCH & FILTER ARTICLES
# =====================
def fetch_and_filter_articles(sent_urls):
    matches = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        website_name = feed.feed.get("title", "Unknown Website")

        for entry in feed.entries:
            url = entry.get("link", "")
            if not url or url in sent_urls:
                continue

            # Fetch full article content
            article_text = fetch_full_text(url)
            title = entry.get("title", "")
            combined_text = f"{title} {article_text}"

            if get_matching_keywords(combined_text):
                summary = summarize_text(combined_text)
                date = entry.get("published", entry.get("updated", "Unknown date"))

                matches.append({
                    "title": title or "No title",
                    "link": url,
                    "date": date,
                    "website": website_name,
                    "summary": summary
                })

                sent_urls.add(url)

    return matches

# =====================
# MAIN
# =====================
def main():
    sent_urls = load_sent_articles()
    articles = fetch_and_filter_articles(sent_urls)

    if not articles:
        print("No new matching articles.")
        return

    save_sent_articles(sent_urls)

    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = f"Website Monitor: {len(articles)} new articles"

    html = "<html><body>"
    html += "<h2>New Matching Articles</h2>"

    for a in articles:
        html += f"""
        <hr>
        <h3>{a['title']}</h3>
        <p>
            <strong>Date:</strong> {a['date']}<br>
            <strong>Website:</strong> {a['website']}<br>
            <strong>URL:</strong> <a href="{a['link']}">{a['link']}</a>
        </p>
        <p>{a['summary']}</p>
        """

    html += "</body></html>"
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_FROM, os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)

    print("Email sent successfully.")

if __name__ == "__main__":
    main()