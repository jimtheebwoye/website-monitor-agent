import feedparser
import smtplib
from email.mime.text import MIMEText
import os
import time
import re
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

# =====================
# INITIALISE SUMMARISER (FREE)
# =====================
print("Loading summarisation model...")
summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn"
)
print("Summariser ready.")

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


def summarize_text(text):
    """
    Free local summarisation.
    Truncates long text to avoid model limits.
    """
    try:
        clean_text = re.sub(r"\s+", " ", text).strip()
        clean_text = clean_text[:3000]  # safety limit

        result = summarizer(
            clean_text,
            max_length=80,
            min_length=30,
            do_sample=False
        )

        return result[0]["summary_text"]

    except Exception as e:
        print(f"Summarisation failed: {e}")
        return "Summary unavailable."


def fetch_and_filter_articles():
    matches = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        website_name = feed.feed.get("title", "Unknown Website")

        for entry in feed.entries:
            text = f"{entry.get('title', '')} {entry.get('summary', '')}"

            if get_matching_keywords(text):
                date = entry.get("published", entry.get("updated", "Unknown date"))

                matches.append({
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", ""),
                    "date": date,
                    "website": website_name,
                    "summary": summarize_text(text)
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
            f"Date: {article['date']}\n"
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
        server.login(EMAIL_FROM, os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)

    print("Email sent successfully.")


if __name__ == "__main__":
    main()