import csv
import json
import logging
import time
from datetime import datetime

import feedparser
import pytz
import redditwarp.SYNC
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

from rcd.config import get_module_config, settings
from rcd.config.log_config import setup_logging

log = logging.getLogger("rec_news")
config = get_module_config("news")

timestamps_file = "timestamps.json"


def get_latest_timestamp(channel):
    try:
        with open(timestamps_file, "r") as f:
            timestamps = json.load(f)
        return timestamps.get(channel, None)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return None


def set_latest_timestamp(channel, timestamp):
    try:
        with open(timestamps_file, "r") as f:
            timestamps = json.load(f)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        timestamps = {}
    timestamps[channel] = timestamp
    with open(timestamps_file, "w") as f:
        json.dump(timestamps, f)


def fetch_reddit_comments(client, subreddit):
    """
    Retrieve comments newer than timestamp from the daily.
    """
    # The daily should be within top 5 hot submissions
    hot = client.p.subreddit.pull.hot(subreddit, amount=5)
    comments = []
    newest_comment_ts = get_latest_timestamp(subreddit)
    for s in hot:
        if "daily" in s.title.lower():
            try:
                tree_node = client.p.comment_tree.fetch(s.id36, sort="new", limit=100)
                for ch in tree_node.children:
                    c = ch.value
                    if newest_comment_ts and c.created_ut <= newest_comment_ts:
                        continue
                    comment = {
                        "id": f"{c.submission.id36}+{c.id36}",
                        "ts": c.created_ut,
                        "author": c.author_display_name,
                        "body": c.body,
                        "subredit": subreddit,
                    }
                    comments.append(comment)
            except Exception as e:
                log.error(f"Error getting comments from {subreddit}: {s.name}")
                log.exception(e)

    if len(comments) > 0:
        new_latest_ts = max(d["ts"] for d in comments if "ts" in d)
        set_latest_timestamp(subreddit, new_latest_ts)

    return comments


def load_feed_urls():
    feed_csvs = {
        "crypto": "../config/crypto_feeds.csv",
        "tradfi": "../config/tradfi_feeds.csv",
    }

    feeds = {
        "crypto": [],
        "tradfi": [],
    }

    for feed_name, csv_file in feed_csvs.items():
        with open(csv_file) as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                feeds[feed_name].append({"source": row[0], "url": row[1]})

    return feeds


def get_article_timestamp(entry):
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return time.mktime(entry.published_parsed)
        else:
            date_format = "%b %d, %Y %H:%M %Z"
            date_obj = datetime.strptime(entry.published, date_format).replace(
                tzinfo=pytz.UTC
            )
            return date_obj.timestamp()
    except Exception as e:
        log.warning(f"Error parsing timestamp: {entry.published_parsed}")
        log.exception(e)
        return None


def fetch_cointelegraph_feed():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

        feed_url = "https://cointelegraph.com/rss"
        response = requests.get(feed_url, headers=headers)
        feed_content = response.content.decode("utf-8")
        return feed_content
    except Exception as e:
        log.exception(e)
        return None


def get_content(rss_content):
    for content in rss_content:
        if "type" in content and content["type"] == "text/plan":
            return content.value

    c = " ".join(content_dict.value for content_dict in rss_content)
    soup = BeautifulSoup(c, "html.parser")
    return soup.get_text()


def fetch_news(feed_list):
    news = []
    for item in feed_list:
        # skip invalid URLs
        if not "http" in item["url"]:
            continue

        latest_ts = get_latest_timestamp(item["source"])
        if latest_ts:
            log.info(
                f"Fetching news from: {item['source']} newer than {datetime.fromtimestamp(latest_ts)}"
            )
        else:
            log.info(f"Fetching all news from {item['source']}")

        # cointelegraph clouflare workaround
        if "cointelegraph" in item["url"]:
            item["url"] = fetch_cointelegraph_feed()

        feed = feedparser.parse(item["url"])
        feed_entries = []
        for entry in feed.entries:
            ts = get_article_timestamp(entry)
            if not ts:
                log.warning(f"Skipping entry from {item['source']} - no timestamp")
                continue
            if latest_ts and ts <= latest_ts:
                continue
            link = entry.link
            title = entry.title if "title" in entry else ""
            summary = entry.summary if "summary" in entry else ""
            published = entry.published if "published" in entry else ""

            if summary:
                soup = BeautifulSoup(summary, "html.parser")
                summary = soup.get_text()

            # The content attribute is a list of content dictionaries
            content = ""
            if "content" in entry:
                content = get_content(entry.content)

            news_entry = {
                "source": item["source"],
                "link": link,
                "title": title,
                "summary": summary,
                "content": content,
                "published": published,
                "ts": ts,
            }
            feed_entries.append(news_entry)

        news.extend(feed_entries)
        if len(feed_entries) > 0:
            new_latest_ts = max(d["ts"] for d in feed_entries if "ts" in d)
            set_latest_timestamp(item["source"], new_latest_ts)

    return news


def save_to_db(db, channel, data):
    try:
        collection = db[channel]
        result = collection.insert_many(data)
        log.info(f"Inserted {len(result.inserted_ids)} into {channel}")
    except Exception as e:
        log.error(f"Error saving {channel} data to database")
        log.exception(e)


def save_to_json(channel, data):
    filename = f"{channel}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def main():
    log.info("Initialising news sync...")
    db_client = None
    try:
        log.info(f"Using database: {config.db_name}")
        db_config = settings[config.db_name]
        db_client = MongoClient(db_config.mongo.conn_str)
        feeds = load_feed_urls()
        reddit_client = redditwarp.SYNC.Client()
        subreddits = config.reddit.subreddits

        while True:
            start = time.perf_counter()
            news = {"crypto": [], "tradfi": []}
            reddit_comments = []
            for feed_name, feed_list in feeds.items():
                news[feed_name] = fetch_news(feed_list)
            for sr in subreddits:
                reddit_comments.extend(fetch_reddit_comments(reddit_client, sr))
            for channel, entries in news.items():
                save_to_db(db_client, f"news_{channel}", entries)
            save_to_db(db_client, "reddit", reddit_comments)
            elapsed = time.perf_counter() - start
            time.sleep(config.fetch_interval - elapsed)
    except Exception as e:
        log.error("Error in the main method")
        log.exception(e)
    finally:
        if db_client:
            db_client.close()


if __name__ == "__main__":
    setup_logging()
    main()
