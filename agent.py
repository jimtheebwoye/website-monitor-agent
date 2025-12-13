import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import time  # needed for retry sleep
import re

# =====================
# CONFIG
# =====================
RSS_FEEDS = [
    "https://www.theregister.com/headlines.atom",                   # The Register headlines
    "https://www.theregister.com/security/headlines.atom",          # The Register security section
    "https://computerweekly.com/rss/All-Computerweekly.xml",        # ComputerWeekly
    "https://cio.com/feed"                                           # CIO.com
]

KEYWORDS = ["SAP", "HMRC", "BTP", "S/4HANA", "Sovereign"]

EMAIL_FROM = "jimtheebwoye@gmail.com"
EMAIL_TO = "jimtheebwoye@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# =====================
# HELPER FUNCTIONS
# =====================
def get_matching_keywords(text):
    """
    Returns a list of keywords that appear in the text.
    - SAP must match as a whole word
    - Others match as substrings
    """
    matches = []
    text_lower = text.lower()

    for keyword in KEYWORDS:
        if keyword == "SAP":
            # Match SAP as a whole word only
            if re.search(r"\bSAP\b", text, re.IGNORECASE):
                matches.append(keyword)
        else:
            if keyword.lower() in text_lower:
                matches.append(keyword)

    return matches
def fetch_and_filter_articles():
    matches = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            text = f"{entry.get('title', '')} {entry.get('summary', '')}"

            if matches_keywords(text):
                matches.append({
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", "")
                })

    return matches
    
    def matches_keywords(text):
    text = text.lower()

    for pattern in KEYWORD_PATTERNS:
        if pattern.search(text):
            return True

    return False
    
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
        body_lines.append(f"{article['title']}\n{article['link']}\n")

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