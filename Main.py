
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
from pathlib import Path

# ============================================================
# TRENDCLIP DAILY — VERSION 2
# Automated trend research and YouTube Shorts script generator
# ============================================================

CHANNEL_NAME = "TrendClip Daily"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-3.5-flash-lite"

NUMBER_OF_SCRIPTS = 5
MAX_TRENDS = 20

RSS_CATEGORIES = [
    "viral internet trends",
    "celebrity news",
    "technology and AI",
    "social media trends",
    "entertainment news",
    "gaming news",
    "sports viral moments",
    "unusual trending stories",
]

# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def safe_filename(text):
    text = re.sub(r"[^a-zA-Z0-9_-]", "_", text)
    return text[:60]


def save_text(filename, content):
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"Saved: {path}")


def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


# ============================================================
# GOOGLE NEWS TREND RESEARCH
# ============================================================

def fetch_google_news(category):
    query = urllib.parse.quote(category)

    url = (
        "https://news.google.com/rss/search?"
        f"q={query}&hl=en-US&gl=US&ceid=US:en"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 TrendClipDaily/2.0"
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read()

        root = ET.fromstring(data)

        results = []

        for item in root.findall(".//item"):
            title = clean_text(item.findtext("title"))
            link = clean_text(item.findtext("link"))
            pub_date = clean_text(item.findtext("pubDate"))
            description = clean_text(item.findtext("description"))

            if not title:
                continue

            results.append({
                "category": category,
                "title": title,
                "link": link,
                "published": pub_date,
                "description": description[:500],
            })

        return results

    except Exception as error:
        log(f"News fetch failed for {category}: {error}")
        return []


def collect_trends():
    log("Starting trend research...")

    trends = []
    seen = set()

    for category in RSS_CATEGORIES:
        log(f"Researching: {category}")

        articles = fetch_google_news(category)

        for article in articles:
            normalized = article["title"].lower()

            if normalized in seen:
                continue

            seen.add(normalized)
            trends.append(article)

        time.sleep(1)

    trends = trends[:MAX_TRENDS]

    log(f"Collected {len(trends)} unique trends.")

    return trends


# ============================================================
# SAVE TREND RESEARCH
# ============================================================

def save_trends(trends):
    csv_path = OUTPUT_DIR / "trends.csv"

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "category",
                "title",
                "link",
                "published",
                "description",
            ],
        )

        writer.writeheader()
        writer.writerows(trends)

    log("Trend spreadsheet saved.")


def create_video_ideas(trends):
    lines = [
        f"{CHANNEL_NAME} — VIDEO IDEAS",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    for index, trend in enumerate(trends, 1):
        lines.extend([
            f"{index}. {trend['title']}",
            f"Category: {trend['category']}",
            f"Source: {trend['link']}",
            "",
        ])

    save_text("video_ideas.txt", "\n".join(lines))


# ============================================================
# GEMINI API
# ============================================================

def call_gemini(prompt):
    if not GEMINI_API_KEY:
        log("GEMINI_API_KEY missing. Using backup scripts.")
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.85,
            "topP": 0.95,
            "maxOutputTokens": 7000,
            "responseMimeType": "application/json",
        },
    }

    body = json.dumps(payload).encode("utf-8")

    for attempt in range(4):
        try:
            request = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "TrendClipDaily/2.0",
                },
                method="POST",
            )

            with urllib.request.urlopen(
                request,
                timeout=90,
            ) as response:

                result = json.loads(response.read().decode("utf-8"))

            candidates = result.get("candidates", [])

            if not candidates:
                raise ValueError("Gemini returned no candidates.")

            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            text = "".join(
                part.get("text", "")
                for part in parts
            )

            if not text.strip():
                raise ValueError("Gemini returned empty text.")

            return text

        except urllib.error.HTTPError as error:
            details = error.read().decode(
                "utf-8",
                errors="replace",
            )

            log(f"Gemini HTTP {error.code}: {details[:500]}")

            if error.code not in (408, 429, 500, 502, 503, 504):
                break

        except Exception as error:
            log(f"Gemini attempt {attempt + 1} failed: {error}")

        if attempt < 3:
            delay = 8 * (2 ** attempt)
            log(f"Retrying in {delay} seconds...")
            time.sleep(delay)

    log("Gemini unavailable after retries.")
    return None


# ============================================================
# SCRIPT GENERATION
# ============================================================

def build_prompt(trends):
    trend_text = "\n".join(
        f"- Category: {item['category']}\n"
        f"  Headline: {item['title']}\n"
        f"  Description: {item['description']}\n"
        f"  Source: {item['link']}"
        for item in trends[:MAX_TRENDS]
    )

    return f"""
You are the head YouTube Shorts writer for {CHANNEL_NAME}.

Create exactly {NUMBER_OF_SCRIPTS} compelling YouTube Shorts scripts.

CHANNEL STYLE:
- Viral internet trends.
- Entertainment and curiosity.
- Social media stories.
- Technology and gaming.
- Interesting current events.

RETENTION RULES:

1. The first sentence must grab attention immediately.
2. Never begin with "Hey guys" or a long introduction.
3. Create curiosity within the first two seconds.
4. Keep sentences short and conversational.
5. Make every sentence move the story forward.
6. Avoid unnecessary explanations.
7. Use a surprising detail or interesting question when supported.
8. Finish with a memorable ending and a natural engagement prompt.
9. Avoid repetitive hooks and endings.
10. Write for spoken narration, not an article.

FACTUAL RULES:

- Use only information supported by the supplied headlines and descriptions.
- Do not invent quotes, numbers, events, dates, or accusations.
- Do not present rumors as confirmed facts.
- If details are uncertain, clearly say so.
- Do not pretend to have independently verified a story.
- Choose the most interesting topics with enough information to make a responsible script.

VIDEO RULES:

- Aim for approximately 90 to 125 spoken words per script.
- Each script should work as a vertical YouTube Short.
- Make the opening powerful.
- Maintain suspense without misleading viewers.
- Include a natural comment or subscribe prompt.
- Make the five scripts cover different stories.

RETURN ONLY VALID JSON.

Use exactly this structure:

{{
  "scripts": [
    {{
      "title": "Short video title",
      "hook": "Opening hook",
      "narration": "Complete spoken narration",
      "caption": "Short thumbnail caption",
      "cta": "Engagement ending",
      "category": "Story category",
      "source": "Original source URL"
    }}
  ]
}}

CURRENT TREND RESEARCH:

{trend_text}
"""


def extract_json(text):
    if not text:
        return None

    text = text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def validate_scripts(data):
    if not isinstance(data, dict):
        return []

    scripts = data.get("scripts", [])

    if not isinstance(scripts, list):
        return []

    valid = []

    for script in scripts:
        if not isinstance(script, dict):
            continue

        title = clean_text(script.get("title"))
        narration = clean_text(script.get("narration"))

        if not title or not narration:
            continue

        if len(narration.split()) < 35:
            continue

        valid.append({
            "title": title,
            "hook": clean_text(script.get("hook")),
            "narration": narration,
            "caption": clean_text(script.get("caption")),
            "cta": clean_text(script.get("cta")),
            "category": clean_text(script.get("category")),
            "source": clean_text(script.get("source")),
        })

    return valid[:NUMBER_OF_SCRIPTS]


# ============================================================
# BACKUP SCRIPTS
# ============================================================

def create_backup_scripts(trends):
    log("Creating local backup scripts...")

    scripts = []

    for trend in trends[:NUMBER_OF_SCRIPTS]:
        title = trend["title"]

        narration = (
            f"Here's a story getting attention right now. "
            f"{title}. "
            "Before jumping to conclusions, remember that "
            "the original reporting matters. "
            "Check the source and look at the full details "
            "before sharing the story. "
            "What do you think about this? "
            "Let us know in the comments, and follow "
            "TrendClip Daily for more trending stories."
        )

        scripts.append({
            "title": title,
            "hook": "This story is getting attention.",
            "narration": narration,
            "caption": "TRENDING NOW",
            "cta": "Tell us what you think.",
            "category": trend["category"],
            "source": trend["link"],
        })

    return scripts


# ============================================================
# SAVE VIDEO SCRIPTS
# ============================================================

def save_scripts(scripts):
    if not scripts:
        log("No scripts available.")
        return False

    # Save all five scripts with their details.

    all_content = [
        f"{CHANNEL_NAME} — SHORTS SCRIPT COLLECTION",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    for index, script in enumerate(scripts, 1):
        all_content.extend([
            "=" * 55,
            f"VIDEO {index}: {script['title']}",
            "=" * 55,
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
            "",
        ])

    save_text(
        "all_shorts_scripts.txt",
        "\n".join(all_content),
    )

    # The existing video_creator.py uses this file.
    # Keep it as plain spoken narration, without JSON
    # or extra script metadata.

    first_script = scripts[0]["narration"].strip()

    save_text(
        "shorts_scripts.txt",
        first_script + "\n",
    )

    # Also save a separate file containing every
    # narration in a simple format.

    narration_content = []

    for index, script in enumerate(scripts, 1):
        narration_content.extend([
            f"VIDEO {index}",
            script["narration"],
            "",
        ])

    save_text(
        "all_narrations.txt",
        "\n".join(narration_content),
    )

    log(f"Successfully saved {len(scripts)} scripts.")

    return True


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():
    print()
    print("=" * 55)
    print(f"       {CHANNEL_NAME.upper()} — VERSION 2")
    print("       AUTOMATED SHORTS RESEARCH SYSTEM")
    print("=" * 55)
    print()

    # STEP 1: Research trending topics.

    trends = collect_trends()

    if not trends:
        log("No trends collected. Stopping.")
        return

    # STEP 2: Save research.

    save_trends(trends)
    create_video_ideas(trends)

    # STEP 3: Generate scripts.

    log("Preparing viral Shorts scripts...")

    prompt = build_prompt(trends)

    response = call_gemini(prompt)

    scripts = []

    if response:
        parsed = extract_json(response)
        scripts = validate_scripts(parsed)

    # STEP 4: Use backup scripts if necessary.

    if len(scripts) < NUMBER_OF_SCRIPTS:
        log("Using backup scripts to fill missing results.")

        backup = create_backup_scripts(trends)

        existing_titles = {
            script["title"].lower()
            for script in scripts
        }

        for script in backup:
            if script["title"].lower() not in existing_titles:
                scripts.append(script)

            if len(scripts) >= NUMBER_OF_SCRIPTS:
                break

    # STEP 5: Save everything.

    if not scripts:
        log("Unable to generate scripts.")
        return

    save_scripts(scripts)

    # STEP 6: Report completion.

    print()
    print("=" * 55)
    print("TRENDCLIP DAILY — RESEARCH COMPLETE")
    print("=" * 55)

    print(f"Trends collected: {len(trends)}")
    print(f"Scripts created: {len(scripts)}")

    print()
    print("OUTPUT FILES:")

    for filename in [
        "trends.csv",
        "video_ideas.txt",
        "shorts_scripts.txt",
        "all_shorts_scripts.txt",
        "all_narrations.txt",
    ]:
        print(f"  - output/{filename}")

    print()
    print("NEXT STEP:")
    print("Run video_creator.py to create your video.")
    print("=" * 55)


if __name__ == "__main__":
    main()
