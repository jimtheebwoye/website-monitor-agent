import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import time
import re
from urllib.parse import urlparse
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

# OpenAI API key must be set as environment variable
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

CHECK_INTERVAL_SECONDS = 2 * 24 * 60 * 60  # 2 days in seconds

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

def summarize_articles_with_gpt(articles, max_words_per_summary=100):
    try:
        prompt_parts = []
        for idx, article in enumerate(articles, start=1):
            prompt_parts.append(
                f"Article {idx}:\nTitle: {article['title']}\n"
                f"Text: {article['text']}\n\n"
            )
        prompt = (
            "Summarize the key points of each article concisely and clearly. "
            f"Limit each summary to {max_words_per_summary} words. "
            "Output in the format:\nArticle 1: summary\nArticle 2: summary\n..."
            "\n\n" + "".join(prompt_parts)
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        content = response.choices[0].message.content.strip()

        # Split summaries by article
        summaries = []
        lines = content.splitlines()
        current_summary = ""
        for line in lines:
            if re.match(r"Article \d+: ?", line):
                if current_summary:
                    summaries.append(current_summary.strip())
                    current_summary = ""
                current_summary = re.sub(r"Article \d+: ?", "", line).strip()
            else:
                current_summary += " " + line.strip()
        if current_summary:
            summaries.append(current_summary.strip())

        while len(summaries) < len(articles):
            summaries.append("Summary not available")

        return summaries

    except Exception as e:
        print(f"GPT summarization failed: {e}")
        summaries = []
        for article in articles:
            sentences = re.split(r'(?<=[.!?])\s+', article['text'])
            summaries.append(" ".join(sentences[:2]))
        return summaries

def fetch_and_filter_articles():
    matches = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        website_name = urlparse(feed_url).netloc

        for entry in feed.entries:
            text = f"{entry.get('title', '')} {entry.get('summary', '')}"
            keywords_found = get_matching_keywords(text)
            if keywords_found:
                published = entry.get('published', 'No date')
                matches.append({
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", ""),
                    "published": published,
                    "website": website_name,
                    "text": text,
                    "keywords": ", ".join(keywords_found)
                })

    return matches

def send_email(articles):
    if not articles:
        print("No matching articles found.")
        return

    summaries = summarize_articles_with_gpt(articles)
    for article, summary in zip(articles, summaries):
        article['summary'] = summary

    body_lines = []
    for article in articles:
        body_lines.append(
            f"Website: {article['website']}\n"
            f"Title: {article['title']}\n"
            f"Date: {article['published']}\n"
            f"Keywords: {article['keywords']}\n"
            f"Summary: {article['summary']}\n"
            f"Link: {article['link']}\n"
            "----------------------------------------\n"
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

# =====================
# MAIN LOOP
# =====================
def main():
    while True:
        print(f"Checking RSS feeds at {datetime.now()}...")
        articles = fetch_and_filter_articles()
        send_email(articles)
        print(f"Sleeping for 2 days...")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()