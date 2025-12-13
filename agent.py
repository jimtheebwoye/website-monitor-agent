import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# =====================
# CONFIG
# =====================
RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml"
]

KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "regulation",
    "security"
]

EMAIL_FROM = "your_email@gmail.com"
EMAIL_TO = "your_email@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# =====================
# LOGIC
# =====================
def is_relevant(text):
    text = text.lower()
    return any(k.lower() in text for k in KEYWORDS)

def summarize(entry):
    # Simple free summary: title + first 2 sentences
    summary = entry.get("summary", "")
    sentences = summary.split(". ")
    return ". ".join(sentences[:2]) + "."

def main():
    articles = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            content = f"{entry.title} {entry.get('summary', '')}"

            if is_relevant(content):
                articles.append(
                    f"📰 {entry.title}\n"
                    f"{summarize(entry)}\n"
                    f"{entry.link}\n"
                )

    if not articles:
        print("No relevant articles found.")
        return

    body = "\n\n".join(articles)
    subject = f"Website Monitor Digest — {datetime.now().strftime('%Y-%m-%d')}"

    msg = MIMEText(body)
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_FROM, "APP_PASSWORD")
        server.send_message(msg)

    print("Email sent.")

if __name__ == "__main__":
    main()
