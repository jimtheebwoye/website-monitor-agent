import feedparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import time
import re
import json
import requests

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

HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")
HF_MODEL_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"

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
# TEXT CLEANING
# =====================
def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text)  # remove HTML
    text = re.sub(r"\s+", " ", text)
    return text.strip()

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
# HUGGING FACE SUMMARY
# =====================
def summarize_text(text):
    if not HF_API_KEY:
        return "Summary unavailable (Hugging Face API key missing)."

    cleaned = clean_text(text)

    # BART needs enough text to work well
    if len(cleaned) < 200:
        return "Summary unavailable (article text too short)."

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": cleaned[:3000],
        "parameters": {
            "max_length": 180,
            "min_length": 90,
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

        data = response.json()

        # Model warming up / HF errors
        if isinstance(data, dict) and "error" in data:
            print("HF API message:", data["error"])
            return "Summary unavailable (model warming up)."

        # Success
        if isinstance(data, list) and "summary_text" in data[0]:
            return data[0]["summary_text"].strip()

        print("Unexpected HF response:", data)
        return "Summary unavailable."

    except Exception as e:
        print(f"Summarisation failed: {e}")
        return "Summary unavailable."

# =====================
# FETCH & FILTER
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

            text = f"""
            Title: {entry.get('title', '')}
            Summary: {entry.get('summary', '')}
            """

            if get_matching_keywords(text):
                summary = summarize_text(text)
                date = entry.get("published", entry.get("updated", "Unknown date"))

                matches.append({
                    "title": entry.get("title", "No title"),
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
    msg["Subject"] = f"Website Monitor: {len(articles)} new matching articles"

    html = "<html><body>"
    html += "<h2>New Articles</h2>"

    for a in articles:
        html += f"""
        <hr>
        <h3>{a['title']}</h3>
        <p>
            <strong>Date:</strong> {a['date']}<br>
            <strong>Website:</strong> {a['website']}<br>
            <strong>URL:</strong>
            <a href="{a['link']}">{a['link']}</a>
        </p>
        <p>{a['summary']}</p>
        """

    html += "</body></html>"
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        for attempt in range(3):
            try:
                server.login(EMAIL_FROM, os.environ["EMAIL_PASSWORD"])
                server.send_message(msg)
                print("Email sent successfully.")
                break
            except smtplib.SMTPAuthenticationError:
                print("Login failed, retrying...")
                time.sleep(5)

if __name__ == "__main__":
    main()