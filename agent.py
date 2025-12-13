import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import time  # needed for retry sleep

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
    """Returns a list of keywords that appear in the text (case-insensitive)."""
    text_lower = text.lower()
    return [k for k in KEYWORDS if k.lower() in text_lower]

def summarize(entry):
    """Return first 2 sentences of summary."""
    summary = entry.get("summary", "")
    sentences = summary.split(". ")
    return ". ".join(sentences[:2]) + "."

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
        for attempt in range(3):
            try:
                server.login(EMAIL_FROM, os.environ["EMAIL_PASSWORD"])
                break
            except smtplib.SMTPAuthenticationError as e:
                print(f"Attempt {attempt+1} login failed. Retrying in 5 seconds...")
                time.sleep(5)
        else:
            print("Failed to login after 3 attempts. Email may not have been sent.")
        server.send_message(msg)

    print("Email sent successfully.")

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
