
import csv
import json
import os
import re
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone


# ==========================================
# TRENDCLIP DAILY SETTINGS
# ==========================================

OUT = Path("output")

MODEL = "gemini-3.5-flash-lite"

FEEDS = [
    (
        "Google Trends US",
        "https://trends.google.com/trending/rss?geo=US"
    ),
    (
        "Reddit Popular",
        "https://www.reddit.com/r/popular/.rss"
    ),
]

MAX_TOPICS = 5


# ==========================================
# COLLECT TRENDING TOPICS
# ==========================================

def get_trends():
    results = []

    for source, url in FEEDS:
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "TrendClipDaily/1.0"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:
                root = ET.fromstring(response.read())

            # RSS feeds
            for item in root.findall(".//item"):
                title = (
                    item.findtext("title") or ""
                ).strip()

                link = (
                    item.findtext("link") or ""
                ).strip()

                if title:
                    results.append([
                        source,
                        title,
                        link
                    ])

            # Atom feeds
            namespace = {
                "a": "http://www.w3.org/2005/Atom"
            }

            for entry in root.findall(
                ".//a:entry",
                namespace
            ):
                title = entry.findtext(
                    "a:title",
                    default="",
                    namespaces=namespace
                ).strip()

                link_node = entry.find(
                    "a:link",
                    namespace
                )

                link = (
                    link_node.get("href", "")
                    if link_node is not None
                    else ""
                )

                if title:
                    results.append([
                        source,
                        title,
                        link
                    ])

            print(
                source,
                "checked successfully"
            )

        except Exception as error:
            print(
                source,
                "could not be checked:",
                error
            )

    unique = {}

    for source, title, link in results:
        unique.setdefault(
            title.lower(),
            [source, title, link]
        )

    return list(unique.values())


# ==========================================
# SAVE TRENDING TOPICS
# ==========================================

def save_trends(trends):
    OUT.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUT / "trends.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Source",
            "Trending Topic",
            "Link"
        ])

        writer.writerows(trends)

    with open(
        OUT / "video_ideas.txt",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "TRENDCLIP DAILY - VIDEO IDEAS\n\n"
        )

        file.write(
            "Research leads only. "
            "Verify facts before publishing.\n\n"
        )

        for number, (
            source,
            title,
            link
        ) in enumerate(trends[:20], 1):

            file.write(
                f"{number}. {title}\n"
            )

            file.write(
                f"Source: {source}\n"
            )

            file.write(
                f"Link: {link}\n\n"
            )

    print("Trending topics saved.")


# ==========================================
# GENERATE AI SCRIPTS
# ==========================================

def create_ai_scripts(trends):
    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY secret is missing."
        )

    selected = trends[:MAX_TOPICS]

    if not selected:
        raise RuntimeError(
            "No trending topics were collected."
        )

    topic_list = "\n".join(
        f"{i}. Topic: {title}\n"
        f"Source: {source}\n"
        f"Link: {link}"
        for i, (source, title, link)
        in enumerate(selected, 1)
    )

    prompt = f"""
You are the professional scriptwriter
for TrendClip Daily, an English-language
YouTube Shorts channel.

Create one original YouTube Shorts script
for EACH of these trend leads:

{topic_list}

LANGUAGE:
- Use natural American English.
- Write everything in English.
- Use clear, simple spoken language.
- Do not mix languages.

FOR EACH TOPIC INCLUDE:

1. Catchy YouTube Shorts title.
2. Opening hook.
3. Original narration for a 30-45 second video.
4. Three suggested visual scenes.
5. Short on-screen captions.
6. Description and hashtags.
7. Fact-check note.

CRITICAL FORMATTING REQUIREMENTS:

For EVERY topic, the narration MUST be
surrounded by these exact markers:

[[NARRATION_START]]
Put the complete spoken narration here.
[[NARRATION_END]]

Do not change the spelling of these markers.
Do not put the markers inside Markdown code blocks.
Do not put titles, captions, visual scenes,
or descriptions inside the narration markers.

Create exactly five scripts when five topics
are supplied.

The narration must:
- Be a complete spoken script.
- Be at least 80 characters long.
- Be suitable for AI voice generation.
- Avoid bullet points.
- Avoid stage directions.
- Avoid complicated symbols.

IMPORTANT CONTENT RULES:
- Treat trends as research leads, not verified facts.
- Never invent facts, quotes, dates, or statistics.
- Flag claims that need verification.
- Do not copy other creators' scripts.
- Do not recommend reposting copyrighted videos.
- Use original commentary and storytelling.
"""

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
            "maxOutputTokens": 8000,
            "temperature": 0.7
        }
    }

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        f"{MODEL}:generateContent"
    )

    result = None

    for attempt in range(5):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key
            },
            method="POST"
        )

        try:
            print(
                f"Contacting Gemini "
                f"(attempt {attempt + 1}/5)..."
            )

            with urllib.request.urlopen(
                request,
                timeout=120
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

            print(
                "Gemini responded successfully!"
            )

            break

        except urllib.error.HTTPError as error:
            details = error.read().decode(
                "utf-8",
                errors="replace"
            )

            if (
                error.code in (429, 500, 502, 503, 504)
                and attempt < 4
            ):
                wait_seconds = 15 * (2 ** attempt)

                print(
                    f"Gemini temporarily unavailable: "
                    f"HTTP {error.code}"
                )

                print(
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)
                continue

            raise RuntimeError(
                f"Gemini API returned HTTP "
                f"{error.code}: {details}"
            )

        except urllib.error.URLError as error:
            if attempt < 4:
                wait_seconds = 15 * (2 ** attempt)

                print(
                    "Gemini connection problem:",
                    error
                )

                print(
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)
                continue

            raise RuntimeError(
                f"Gemini connection failed: {error}"
            )

    if result is None:
        raise RuntimeError(
            "Gemini failed after five attempts."
        )

    candidates = result.get(
        "candidates",
        []
    )

    if not candidates:
        raise RuntimeError(
            "Gemini returned no script candidates."
        )

    parts = candidates[0].get(
        "content",
        {}
    ).get(
        "parts",
        []
    )

    scripts = "\n".join(
        part["text"]
        for part in parts
        if "text" in part
    )

    if not scripts.strip():
        raise RuntimeError(
            "Gemini returned an empty script."
        )

    return scripts


# ==========================================
# EXTRACT NARRATION
# ==========================================

def extract_first_narration(scripts):
    pattern = re.compile(
        r"\[\[NARRATION_START\]\]"
        r"(.*?)"
        r"\[\[NARRATION_END\]\]",
        re.I | re.S
    )

    matches = pattern.findall(scripts)

    if not matches:
        raise RuntimeError(
            "Gemini did not return narration markers. "
            "The full AI response was saved for inspection."
        )

    narration = matches[0]

    narration = re.sub(
        r"\s+",
        " ",
        narration
    ).strip()

    if len(narration) < 80:
        raise RuntimeError(
            "The first narration is too short."
        )

    print(
        "Narration extracted successfully."
    )

    print(
        "Narration length:",
        len(narration),
        "characters"
    )

    return narration


# ==========================================
# SAVE ALL SCRIPTS AND VIDEO NARRATION
# ==========================================

def save_scripts(scripts):
    OUT.mkdir(
        parents=True,
        exist_ok=True
    )

    # Preserve the complete Gemini response.
    full_script_path = (
        OUT / "all_shorts_scripts.txt"
    )

    full_script_path.write_text(
        scripts,
        encoding="utf-8"
    )

    print(
        "All five scripts saved."
    )

    # Extract the first video's narration.
    narration = extract_first_narration(
        scripts
    )

    # Write a clean file in the exact format
    # expected by video_creator.py.
    narration_path = (
        OUT / "shorts_scripts.txt"
    )

    narration_path.write_text(
        "TRENDCLIP DAILY - VIDEO SCRIPT\n\n"
        "Original Narration:\n"
        f"{narration}\n",
        encoding="utf-8"
    )

    print(
        "Video narration saved successfully."
    )

    print(
        "Location:",
        narration_path
    )


# ==========================================
# MAIN PROGRAM
# ==========================================

def main():
    print("================================")
    print("       TRENDCLIP DAILY")
    print("       AI SCRIPT GENERATOR")
    print("================================")

    print(
        "Research time:",
        datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC")
    )

    OUT.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\nCollecting trending topics...")

    trends = get_trends()

    if not trends:
        raise RuntimeError(
            "No trending topics were collected. "
            "Both trend feeds may be unavailable."
        )

    print(
        "Topics collected:",
        len(trends)
    )

    save_trends(trends)

    print("\nGenerating AI scripts...")

    scripts = create_ai_scripts(
        trends
    )

    print("\nSaving scripts...")

    save_scripts(scripts)

    print("\n================================")
    print("SUCCESS: AI SCRIPTS CREATED")
    print("================================")

    print(
        "All scripts:",
        OUT / "all_shorts_scripts.txt"
    )

    print(
        "Video narration:",
        OUT / "shorts_scripts.txt"
    )


if __name__ == "__main__":
    main()
