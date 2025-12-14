import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import time
import re
import json
import hashlib
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

STATE_FILE = "sent_articles.json"

# =====================
# STATE (DEDUPLICATION)
# =====================
def load_sent_articles():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_sent_articles(sent_ids):
    with open(STATE_FILE, "w") as f:
        json.dump(list(sent_ids), f)

def article_id(link):
    return hashlib.sha256(link.encode()).hexdigest()

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
# SUMMARISATION
# =====================
def summarize_text(text):
    if not OPENAI_API_KEY:
        return "Summary unavailable (OpenAI API key missing)."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a technology analyst summarising news for senior IT leaders."
                },
                {
                    "role": "user",
                    "content": f"Summarise the key facts and implications of this article in 4–5 concise sentences:\n\n{text}"
                }
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"OpenAI summarisation failed: {e}")
        return "Summary unavailable."

# =====================
# FETCH + FILTER
# =====================
def fetch_and_filter_articles(sent_ids):
    results = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        website = feed.feed.get("title", "Unknown source")

        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")

            # CIO.com FIX (Option 1)
            if not summary or len(summary.strip()) < 100:
                summary = title

            text = f"{title}. {summary}"

            if not get_matching_keywords(text):
                continue

            aid = article_id(link)
            if aid in sent_ids:
                continue

            published = entry.get("published", entry.get("updated", "Unknown date"))

            results.append({
                "id": aid,
                "title": title,
                "link": link,
                "date": published,
                "website": website,
                "summary": summarize_text(text)
            })

    return results

# =====================
# EMAIL
# =====================
def send_email(articles):
    rows = ""

    for a in articles:
        rows += f"""
        <tr>
            <td style="padding:15px;border-bottom:1px solid #ddd;">
                <h3>{a['title']}</h3>
                <p><b>Date:</b> {a['date']}<br>
                <b>Source:</b> {a['website']}<br>
                <b>URL:</b> <a href="{a['link']}">{a['link']}</a></p>
                <p>{a['summary']}</p>
            </td>
        </tr>
        """

    html = f"""
    <html>
    <body style="font-family:Arial, sans-serif;">
        <h2>Website Monitor – {len(articles)} new articles</h2>
        <table width="100%" cellpadding="0" cellspacing="0">
            {rows}
        </table>
    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = f"Website Monitor: {len(articles)} new articles"

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        for attempt in range(3):
            try:
                server.login(EMAIL_FROM, os.environ["EMAIL_PASSWORD"])
                server.send_message(msg)
                return
            except smtplib.SMTPAuthenticationError:
                time.sleep(5)

        raise RuntimeError("Email authentication failed")

# =====================
# MAIN
# =====================
def main():
    sent_ids = load_sent_articles()
    articles = fetch_and_filter_articles(sent_ids)

    if not articles:
        print("No new matching articles.")
        return

    send_email(articles)

    for a in articles:
        sent_ids.add(a["id"])

    save_sent_articles(sent_ids)
    print(f"Sent {len(articles)} new articles.")

if __name__ == "__main__":
    main()