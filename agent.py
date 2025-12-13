import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import time
import re
import openai

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

def summarize_text(text):
    """Use OpenAI to summarize the text. Returns summary string or fallback."""
    if not OPENAI_API_KEY:
        return "Summary unavailable (API key missing)."
    try:
        prompt = f"Summarize the key points of this text in 2-3 sentences:\n\n{text}"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
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
        website_name = feed.feed.get("title", "Unknown Website")

        for entry in feed.entries:
            text = f"{entry.get('title', '')} {entry.get('summary', '')}"

            if get_matching_keywords(text):
                # extract date in a readable format
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
        print("Email sent successfully.")

if __name__ == "__main__":
    main()