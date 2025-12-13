import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import time
import re
import openai  # Make sure openai is installed: pip install openai

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

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# =====================
# HELPER FUNCTIONS
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

def summarize_article(article_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Summarize this article in 2-3 concise points:\n\n{article_text}"}],
            max_tokens=150
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"OpenAI summarization failed: {e}")
        return "Summary unavailable."

def fetch_and_filter_articles():
    matches = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            text = f"{entry.get('title', '')} {entry.get('summary', '')}"
            matched_keywords = get_matching_keywords(text)
            if matched_keywords:
                # Summarize using ChatGPT
                summary = summarize_article(text)
                matches.append({
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", "No date"),
                    "website": feed.feed.get("title", "Unknown"),
                    "summary": summary
                })

    return matches

# =====================
# MAIN FUNCTION
# =====================
def main():
    articles = fetch_and_filter_articles()

    if not articles:
        print("No matching articles found.")
        return

    body_lines = []
    for article in articles:
        body_lines.append(
            f"Title: {article['title']}\n"
            f"Date: {article['published']}\n"
            f"Website: {article['website']}\n"
            f"URL: {article['link']}\n"
            f"Summary:\n{article['summary']}\n"
            "----------------------\n"
        )

    body = "\n".join(body_lines)
    subject = f"Website Monitor: {len(articles)} matching articles"

    msg = MIMEText(body)
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        logged_in = False

        for attempt in range(3):
            try:
                server.login(EMAIL_FROM, os.environ["EMAIL_PASSWORD"])
                logged_in = True
                break
            except smtplib.SMTPAuthenticationError:
                print(f"Attempt {attempt + 1} login failed. Retrying in 5 seconds...")
                time.sleep(5)

        if not logged_in:
            raise RuntimeError(
                "Could not authenticate with Gmail SMTP. Aborting email send."
            )

        server.send_message(msg)

if __name__ == "__main__":
    main()