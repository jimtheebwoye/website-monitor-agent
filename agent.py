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

# =====================
# MAIN FUNCTION
# =====================
def main():
    articles = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            content = f"{entry.title} {entry.get('summary', '')}"
            matched_keywords = get_matching_keywords(content)
            if matched_keywords:
                keyword_str = ", ".join(matched_keywords)
                articles.append(
                    f"📰 {entry.title}\nMatched keywords: {keyword_str}\n"
                    f"{summarize(entry)}\n{entry.link}\n"
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

    # =====================
    # EMAIL WITH RETRY
    # =====================
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

# =====================
# RUN SCRIPT
# =====================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("ERROR:")
        traceback.print_exc()
        raise e
