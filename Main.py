
import csv
import json
import os
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone


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

MODEL = "gemini-3.5-flash-lite"


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
                timeout=20
            ) as response:
                root = ET.fromstring(response.read())

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

            ns = {
                "a": "http://www.w3.org/2005/Atom"
            }

            for entry in root.findall(
                ".//a:entry",
                ns
            ):
                title = entry.findtext(
                    "a:title",
                    default="",
                    namespaces=ns
                ).strip()

                link_node = entry.find(
                    "a:link",
                    ns
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

            print(source, "checked successfully")

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


def create_ai_scripts(trends):
    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY secret is missing."
        )

    selected = trends[:5]

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
for each of these five trend leads:

{topic_list}

LANGUAGE REQUIREMENTS:
- Write EVERYTHING in natural English.
- Use American English spelling and grammar.
- Titles must be English.
- Narration must be English.
- Captions must be English.
- Descriptions must be English.
- Hashtags must be appropriate for an
  English-language audience.
- Never insert foreign-language phrases,
  subtitles, or translations.
- Do not mix languages.
- Use clear, simple wording.

For EACH topic provide:

1. Catchy YouTube Shorts title.
2. Opening hook that grabs attention.
3. Original narration designed for a
   30-45 second video.
4. Three suggested visual scenes that can
   be created with original or licensed material.
5. Short on-screen captions.
6. Description and relevant hashtags.
7. A fact-check note listing what needs
   verification before publishing.

IMPORTANT RULES:
- Treat trends as research leads,
  not verified facts.
- Never invent facts, quotes, dates,
  or statistics.
- Clearly flag claims that need checking.
- Add original commentary and storytelling.
- Do not copy social media posts or
  other creators' scripts.
- Do not recommend downloading or
  reposting copyrighted videos.
- Make scripts engaging, natural,
  and easy to narrate.
- Separate each script clearly.
- Keep narration suitable for spoken English.
- Avoid unusual symbols and complicated words.
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
            "maxOutputTokens": 6000,
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

            print("Gemini responded successfully!")
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
                    f"Gemini temporarily unavailable "
                    f"(HTTP {error.code})."
                )

                print(
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)
                continue

            raise RuntimeError(
                f"Gemini API returned HTTP "
                f"{error.code} after "
                f"{attempt + 1} attempt(s): "
                f"{details}"
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
                f"Gemini connection failed "
                f"after 5 attempts: {error}"
            )

    if result is None:
        raise RuntimeError(
            "Gemini failed after 5 attempts."
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


def main():
    print("TRENDCLIP DAILY")
    print("ENGLISH-ONLY SCRIPT GENERATION")

    print(
        "Research:",
        datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC")
    )

    trends = get_trends()

    Path("output").mkdir(
        exist_ok=True
    )

    with open(
        "output/trends.csv",
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
        "output/video_ideas.txt",
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

    print(
        "Topics collected:",
        len(trends)
    )

    scripts = create_ai_scripts(trends)

    with open(
        "output/shorts_scripts.txt",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "TRENDCLIP DAILY - AI SHORTS SCRIPTS\n\n"
        )

        file.write(scripts)

    print("AI scripts successfully created!")
    print("Results saved in output/")


if __name__ == "__main__":
    main()
