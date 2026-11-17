
import csv
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

# ============================================================
# TRENDCLIP AI — VERSION 3
# Advanced trend research and Shorts script generator
# ============================================================

CHANNEL_NAME = "TrendClip Daily"
VERSION = "3.0"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
).strip()

NUMBER_OF_SCRIPTS = 5
MAX_TRENDS = 30
MIN_SCRIPT_WORDS = 65
MAX_SCRIPT_WORDS = 105

RSS_CATEGORIES = [
    "viral internet trends today",
    "TikTok trending stories",
    "YouTube trending creators",
    "celebrity entertainment news",
    "technology artificial intelligence news",
    "gaming news and updates",
    "social media controversies news",
    "viral unusual stories",
    "streamer news and viral moments",
    "internet culture trending stories",
]

# ============================================================
# LOGGING AND TEXT HELPERS
# ============================================================

def log(message):
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] {message}",
        flush=True
    )


def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def safe_filename(text):
    text = re.sub(r"[^a-zA-Z0-9_-]", "_", text)
    return text[:60]


def save_text(filename, content):
    path = OUTPUT_DIR / filename

    path.write_text(
        content,
        encoding="utf-8"
    )

    log(f"Saved: {path}")


def word_count(text):
    return len(text.split())


def normalize_title(title):
    return re.sub(
        r"[^a-z0-9]",
        "",
        title.lower()
    )


# ============================================================
# GOOGLE NEWS RESEARCH
# ============================================================

def fetch_google_news(category):

    query = urllib.parse.quote(category)

    url = (
        "https://news.google.com/rss/search?"
        f"q={query}"
        "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 TrendClipAI/3.0"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=25
        ) as response:

            data = response.read()

        root = ET.fromstring(data)

        results = []

        for item in root.findall(".//item"):

            title = clean_text(
                item.findtext("title")
            )

            link = clean_text(
                item.findtext("link")
            )

            published = clean_text(
                item.findtext("pubDate")
            )

            description = clean_text(
                item.findtext("description")
            )

            if not title or not link:
                continue

            results.append({
                "category": category,
                "title": title,
                "link": link,
                "published": published,
                "description": description[:700]
            })

        return results

    except Exception as error:

        log(
            f"Research error for {category}: {error}"
        )

        return []


def get_article_age(published):

    try:

        article_date = parsedate_to_datetime(
            published
        )

        if article_date.tzinfo is None:
            article_date = article_date.replace(
                tzinfo=timezone.utc
            )

        age = (
            datetime.now(timezone.utc) - article_date
        ).total_seconds() / 3600

        return max(0, age)

    except Exception:
        return 9999


def score_trend(article):

    title = article["title"].lower()

    age = get_article_age(
        article["published"]
    )

    score = 0

    # Prefer recent reporting.

    if age <= 6:
        score += 40
    elif age <= 24:
        score += 30
    elif age <= 72:
        score += 15
    elif age <= 168:
        score += 5

    # Reward interesting subject matter.

    interesting_words = [
        "viral",
        "shocking",
        "reveals",
        "unexpected",
        "breaking",
        "announces",
        "controversy",
        "million",
        "secret",
        "surprise",
        "update",
        "finally",
        "internet",
        "streamer",
        "creator",
        "tiktok",
        "youtube",
        "ai",
        "gaming",
        "trend"
    ]

    for word in interesting_words:
        if word in title:
            score += 3

    # Prefer headlines with enough information.

    if len(title.split()) >= 7:
        score += 5

    if len(article["description"]) > 100:
        score += 8

    return score


def collect_trends():

    log("Starting TrendClip AI research...")

    trends = []
    seen = set()

    for category in RSS_CATEGORIES:

        log(f"Researching: {category}")

        articles = fetch_google_news(category)

        for article in articles:

            normalized = normalize_title(
                article["title"]
            )

            if normalized in seen:
                continue

            seen.add(normalized)

            article["score"] = score_trend(
                article
            )

            trends.append(article)

        time.sleep(1)

    trends.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    trends = trends[:MAX_TRENDS]

    log(
        f"Collected {len(trends)} unique stories."
    )

    return trends


# ============================================================
# SAVE RESEARCH
# ============================================================

def save_trends(trends):

    path = OUTPUT_DIR / "trends.csv"

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        fields = [
            "category",
            "title",
            "link",
            "published",
            "description",
            "score"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()

        for trend in trends:
            writer.writerow({
                field: trend.get(field, "")
                for field in fields
            })

    log("Trend spreadsheet saved.")


def create_video_ideas(trends):

    lines = [
        f"{CHANNEL_NAME} — VIDEO IDEAS",
        f"Version: {VERSION}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    for index, trend in enumerate(
        trends,
        1
    ):

        lines.extend([
            f"{index}. {trend['title']}",
            f"Category: {trend['category']}",
            f"Score: {trend['score']}",
            f"Published: {trend['published']}",
            f"Source: {trend['link']}",
            "",
        ])

    save_text(
        "video_ideas.txt",
        "\n".join(lines)
    )


# ============================================================
# GEMINI AI
# ============================================================

def call_gemini(prompt):

    if not GEMINI_API_KEY:

        log(
            "GEMINI_API_KEY missing. "
            "Using backup scripts."
        )

        return None

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.9,
            "topP": 0.95,
            "maxOutputTokens": 7000,
            "responseMimeType": "application/json"
        }
    }

    body = json.dumps(
        payload
    ).encode("utf-8")

    for attempt in range(4):

        try:

            request = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "TrendClipAI/3.0"
                },
                method="POST"
            )

            with urllib.request.urlopen(
                request,
                timeout=90
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

            candidates = result.get(
                "candidates",
                []
            )

            if not candidates:
                raise ValueError(
                    "Gemini returned no candidates."
                )

            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            response_text = "".join(
                part.get("text", "")
                for part in parts
            )

            if not response_text.strip():
                raise ValueError(
                    "Gemini returned empty text."
                )

            return response_text

        except urllib.error.HTTPError as error:

            details = error.read().decode(
                "utf-8",
                errors="replace"
            )

            log(
                f"Gemini HTTP {error.code}: "
                f"{details[:400]}"
            )

            if error.code not in (
                408, 429, 500, 502, 503, 504
            ):
                break

        except Exception as error:

            log(
                f"Gemini attempt "
                f"{attempt + 1} failed: {error}"
            )

        if attempt < 3:

            delay = 8 * (2 ** attempt)

            log(
                f"Retrying in {delay} seconds..."
            )

            time.sleep(delay)

    log("Gemini unavailable after retries.")

    return None


# ============================================================
# AI SCRIPT PROMPT
# ============================================================

def build_prompt(trends):

    trend_text = "\n\n".join(
        (
            f"STORY {index}\n"
            f"Category: {item['category']}\n"
            f"Headline: {item['title']}\n"
            f"Description: {item['description']}\n"
            f"Published: {item['published']}\n"
            f"Source: {item['link']}"
        )
        for index, item in enumerate(
            trends[:MAX_TRENDS],
            1
        )
    )

    return f"""
You are the lead viral YouTube Shorts writer
for {CHANNEL_NAME}.

Your job is to create five highly engaging,
professional YouTube Shorts scripts.

CHANNEL:
{CHANNEL_NAME}

STYLE:
- Energetic.
- Entertaining.
- Modern internet culture.
- Creator and streamer stories.
- Celebrity and entertainment updates.
- Technology and gaming.
- Interesting trending stories.

THE FIRST TWO SECONDS ARE CRITICAL.

HOOK REQUIREMENTS:

1. Start with an attention-grabbing sentence.
2. Create immediate curiosity.
3. Never start with "Hey guys".
4. Never start with "Welcome back".
5. Avoid generic openings.
6. Make viewers want to hear the next sentence.

RETENTION REQUIREMENTS:

1. Every sentence must add something interesting.
2. Keep narration conversational.
3. Use short, punchy sentences.
4. Avoid unnecessary background information.
5. Build curiosity throughout the story.
6. Use natural transitions.
7. Include an interesting payoff.
8. Finish with an engaging question or CTA.
9. Do not repeat the same hook structure.
10. Avoid robotic or overly formal writing.

SCRIPT LENGTH:

- Target 75 to 100 spoken words.
- Never exceed 105 words.
- Aim for approximately 30 to 45 seconds.
- Write for voiceover narration.
- Do not include stage directions.

FACTUAL REQUIREMENTS:

- Only use facts supported by the supplied research.
- Never invent numbers, quotes, dates or events.
- Never turn speculation into confirmed information.
- Do not invent reactions or public opinions.
- Be careful with allegations and controversies.
- Do not exaggerate what the reporting actually says.
- If a story lacks sufficient information, skip it.
- Use the original source URL supplied with each story.

STORY SELECTION:

- Choose five different interesting stories.
- Prefer recent and well-supported reporting.
- Avoid duplicate topics.
- Prefer stories with enough detail for narration.
- Do not choose five stories about the same subject.

TITLE REQUIREMENTS:

- Short.
- Curiosity-driven.
- Easy to understand.
- Suitable for YouTube Shorts.

THUMBNAIL CAPTION:

- Maximum five words.
- Easy to read.
- Interesting and relevant.

CTA REQUIREMENTS:

- Encourage comments naturally.
- Avoid begging for likes.
- Use different endings.
- Keep the CTA conversational.

RETURN ONLY VALID JSON.

Use this exact structure:

{{
  "scripts": [
    {{
      "title": "Video title",
      "hook": "Opening hook",
      "narration": "Complete spoken narration",
      "caption": "Thumbnail caption",
      "cta": "Engagement ending",
      "category": "Story category",
      "source": "Original source URL"
    }}
  ]
}}

CURRENT RESEARCH:

{trend_text}
"""


# ============================================================
# JSON EXTRACTION AND VALIDATION
# ============================================================

def extract_json(text):

    if not text:
        return None

    text = text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        return json.loads(
            text[start:end + 1]
        )

    except json.JSONDecodeError:
        return None


def validate_scripts(data):

    if not isinstance(data, dict):
        return []

    scripts = data.get("scripts", [])

    if not isinstance(scripts, list):
        return []

    valid = []

    seen_titles = set()

    for script in scripts:

        if not isinstance(script, dict):
            continue

        title = clean_text(
            script.get("title")
        )

        narration = clean_text(
            script.get("narration")
        )

        hook = clean_text(
            script.get("hook")
        )

        caption = clean_text(
            script.get("caption")
        )

        if not title or not narration:
            continue

        if word_count(narration) < MIN_SCRIPT_WORDS:
            log(
                f"Skipping short script: {title}"
            )
            continue

        if word_count(narration) > MAX_SCRIPT_WORDS:
            log(
                f"Skipping oversized script: {title}"
            )
            continue

        normalized = normalize_title(title)

        if normalized in seen_titles:
            continue

        seen_titles.add(normalized)

        valid.append({
            "title": title,
            "hook": hook or narration.split(".")[0],
            "narration": narration,
            "caption": caption or "TRENDING NOW",
            "cta": clean_text(
                script.get("cta")
            ),
            "category": clean_text(
                script.get("category")
            ),
            "source": clean_text(
                script.get("source")
            )
        })

    return valid[:NUMBER_OF_SCRIPTS]


# ============================================================
# BACKUP SCRIPT GENERATOR
# ============================================================

def create_backup_scripts(trends):

    log("Creating backup scripts...")

    scripts = []

    for trend in trends:

        title = trend["title"]

        description = trend["description"]

        if not description:
            description = (
                "The original report provides "
                "additional details about this story."
            )

        narration = (
            f"This is one story worth paying attention to. "
            f"{title}. "
            f"Here's what the available reporting says. "
            f"{description} "
            f"There's more to this story than just the headline, "
            f"so make sure you check the original source "
            f"before drawing conclusions. "
            f"What do you think about this development? "
            f"Drop your thoughts in the comments and follow "
            f"TrendClip Daily for more updates."
        )

        scripts.append({
            "title": title,
            "hook": "This story is worth paying attention to.",
            "narration": narration,
            "caption": "TRENDING RIGHT NOW",
            "cta": "What do you think? Tell us below.",
            "category": trend["category"],
            "source": trend["link"]
        })

        if len(scripts) >= NUMBER_OF_SCRIPTS:
            break

    return scripts


# ============================================================
# SAVE ALL SCRIPTS
# ============================================================

def save_scripts(scripts):

    if not scripts:
        log("No scripts available.")
        return False

    generated = datetime.now(
        timezone.utc
    ).isoformat()

    # Complete script collection.

    all_content = [
        f"{CHANNEL_NAME} — VERSION {VERSION}",
        f"Generated: {generated}",
        ""
    ]

    for index, script in enumerate(
        scripts,
        1
    ):

        all_content.extend([
            "=" * 60,
            f"VIDEO {index}: {script['title']}",
            "=" * 60,
            "",
            f"HOOK: {script['hook']}",
            "",
            f"CAPTION: {script['caption']}",
            "",
            "NARRATION:",
            script["narration"],
            "",
            f"CTA: {script['cta']}",
            f"CATEGORY: {script['category']}",
            f"SOURCE: {script['source']}",
            ""
        ])

    save_text(
        "all_shorts_scripts.txt",
        "\n".join(all_content)
    )

    # IMPORTANT:
    # video_creator.py reads this file.
    # Keep the Original Narration heading.

    first = scripts[0]

    video_content = (
        f"TRENDCLIP DAILY - VIDEO SCRIPT\n\n"
        f"Title: {first['title']}\n\n"
        f"Caption: {first['caption']}\n\n"
        f"Original Narration:\n"
        f"{first['narration']}\n"
    )

    save_text(
        "shorts_scripts.txt",
        video_content
    )

    # Save all five narrations.

    narration_content = []

    for index, script in enumerate(
        scripts,
        1
    ):

        narration_content.extend([
            f"VIDEO {index}: {script['title']}",
            "Original Narration:",
            script["narration"],
            ""
        ])

    save_text(
        "all_narrations.txt",
        "\n".join(narration_content)
    )

    # Machine-readable script collection.

    save_text(
        "scripts.json",
        json.dumps(
            {
                "channel": CHANNEL_NAME,
                "version": VERSION,
                "generated": generated,
                "scripts": scripts
            },
            indent=2,
            ensure_ascii=False
        )
    )

    log(
        f"Successfully saved {len(scripts)} scripts."
    )

    return True


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print()

    print("=" * 60)
    print("          TRENDCLIP AI — VERSION 3")
    print("       ADVANCED SHORTS GENERATION SYSTEM")
    print("=" * 60)

    print()

    log("Initializing TrendClip AI...")

    # STEP 1: Research.

    trends = collect_trends()

    if not trends:

        log("No trends found. Stopping.")

        raise RuntimeError(
            "Google News research returned no stories."
        )

    # STEP 2: Save research.

    save_trends(trends)

    create_video_ideas(trends)

    # STEP 3: Generate AI scripts.

    log("Preparing five Shorts scripts...")

    prompt = build_prompt(trends)

    response = call_gemini(prompt)

    scripts = []

    if response:

        save_text(
            "gemini_response.json",
            response
        )

        parsed = extract_json(response)

        scripts = validate_scripts(
            parsed
        )

        log(
            f"AI generated {len(scripts)} valid scripts."
        )

    # STEP 4: Fill missing scripts.

    if len(scripts) < NUMBER_OF_SCRIPTS:

        log(
            "Filling missing scripts using backup generator."
        )

        backup = create_backup_scripts(
            trends
        )

        existing_titles = {
            normalize_title(script["title"])
            for script in scripts
        }

        for script in backup:

            normalized = normalize_title(
                script["title"]
            )

            if normalized in existing_titles:
                continue

            scripts.append(script)

            existing_titles.add(normalized)

            if len(scripts) >= NUMBER_OF_SCRIPTS:
                break

    # STEP 5: Save final scripts.

    if not scripts:

        log("Unable to generate scripts.")

        raise RuntimeError(
            "No usable scripts were generated."
        )

    success = save_scripts(scripts)

    if not success:

        raise RuntimeError(
            "Could not save generated scripts."
        )

    # STEP 6: Completion report.

    print()

    print("=" * 60)
    print("       TRENDCLIP AI — GENERATION COMPLETE")
    print("=" * 60)

    print()

    print(f"Version: {VERSION}")
    print(f"Channel: {CHANNEL_NAME}")
    print(f"Trends collected: {len(trends)}")
    print(f"Scripts created: {len(scripts)}")

    print()

    print("OUTPUT FILES:")

    files = [
        "trends.csv",
        "video_ideas.txt",
        "shorts_scripts.txt",
        "all_shorts_scripts.txt",
        "all_narrations.txt",
        "scripts.json"
    ]

    if response:
        files.append("gemini_response.json")

    for filename in files:

        print(
            f"  output/{filename}"
        )

    print()

    print("NEXT STEP:")
    print("Run video_creator.py to create your Short.")

    print()

    print("=" * 60)


if __name__ == "__main__":

    main()
