import feedparser
import smtplib
from email.mime.text import MIMEText
import os
import time
import re
import json
from datetime import datetime
from transformers import pipeline

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

SENT_ARTICLES_FILE = "sent_articles.json"

# =====================
# LOAD SUMMARISER
# =====================
print("Loading summarisation model...")
summariser = pipeline("summarization", model="facebook/bart-large-cnn")
print("Summariser ready.")

# =====================
# UTILITIES
# =====================
def load_sent_articles():
    if not os.path.exists(SENT_ARTICLES_FILE):
        return set()
    with open(SENT_ARTICLES_FILE, "r") as f:
        return set(json.load(f))

def save_sent_articles(urls):
    with open(SENT_ARTICLES_FILE, "w") as f:
        json.dump(list(urls), f)

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

def summarize_text(text):
    try:
        prompt_text = (
            "Summarise the following article in 4–6 sentences. "
            "Include the key facts, organisations involved, and why it matters:\n\n"
            + text
        )

        summary = summariser(
            prompt_text,
            max_length=200,
            min_length=120,
            do_sample=False
        )[0]["summary_text"]

        return summary
    except Exception as e:
        print(f"Summarisation failed: {e}")
        return "Summary unavailable."

# =====================
# FETCH + FILTER
# =====================
def fetch_and_filter_articles(sent_urls):
    matches = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        website_name = feed.feed.get("title", "Unknown Website")

        for entry in feed.entries:
            url = entry.get("link", "")
            if not url or url in sent_urls:
                continue  # deduplication

            text = f"{entry.get('title', '')} {entry.get('summary', '')}"

            if get_matching_keywords(text):
                date = entry.get("published", entry.get("updated", "Unknown date"))

                matches.append({
                    "title": entry.get("title", "No title"),
                    "link": url,
                    "date": date,
                    "website": website_name,
                    "summary": summarize_text(text)
                })

    return matches

# =====================
# EMAIL (HTML)
# =====================
def build_html_email(articles):
    html = """
    <html>
    <body style="font-family: Arial, sans-serif;">
      <h2>Website Monitor – Matching Articles</h2>
      <hr>
    """

    for article in articles:
        html += f"""
        <h3>{article['title']}</h3>
        <p>
          <strong>Date:</strong> {article['date']}<br>
          <strong>Website:</strong> {article['website']}<br>
          <strong>URL:</strong> <a href="{article['link']}">{article['link']}</a>
        </p>
        <p>{article['summary']}</p>
        <hr>
        """

    html += "</body></html>"
    return html

# =====================
# MAIN
# =====================
def main():
    sent_urls = load_sent_articles()

    articles = fetch_and_filter_articles(sent_urls)

    if not articles:
        print("No new matching articles found.")
        return

    html_body = build_html_email(articles)

    msg = MIMEText(html_body, "html")
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = f"Website Monitor: {len(articles)} new articles"

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        for attempt in range(3):
            try:
                server.login(EMAIL_FROM, os.environ["EMAIL_PASSWORD"])
                break
            except smtplib.SMTPAuthenticationError:
                time.sleep(5)

        server.send_message(msg)

    # Save sent URLs
    for article in articles:
        sent_urls.add(article["link"])

    save_sent_articles(sent_urls)

    print("Email sent successfully.")

if __name__ == "__main__":
    main()