
import csv
import json
import os
import re
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

# ==========================================
# TRENDCLIP DAILY - CREATOR CULTURE EDITION
# ==========================================

MODEL = "gemini-3.5-flash-lite"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Creator-focused Reddit feeds
FEEDS = [
    ("LivestreamFail", "https://www.reddit.com/r/LivestreamFail/.rss?limit=25"),
    ("TikTokCringe", "https://www.reddit.com/r/TikTokCringe/.rss?limit=25"),
    ("TikTok", "https://www.reddit.com/r/TikTok/.rss?limit=25"),
    ("YouTubeDrama", "https://www.reddit.com/r/YouTubeDrama/.rss?limit=25"),
    ("InfluencerDrama", "https://www.reddit.com/r/InfluencerDrama/.rss?limit=25"),
    ("Streamers", "https://www.reddit.com/r/streamers/.rss?limit=25"),
]

HEADERS = {
    "User-Agent": "TrendClipDaily/1.0 (content research)"
}


def fetch_url(url, timeout=20):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def get_trends():
    """Collect creator and viral-content topics from public feeds."""
    results = []
    seen = set()

    for source, url in FEEDS:
        try:
            print(f"Checking {source}...")

            raw = fetch_url(url)
            root = ET.fromstring(raw)

            for item in root.iter():
                tag = item.tag.split("}")[-1]

                if tag not in ("item", "entry"):
                    continue

                title = ""
                link = ""

                for child in item:
                    child_tag = child.tag.split("}")[-1]

                    if child_tag == "title":
                        title = (child.text or "").strip()

                    elif child_tag == "link":
                        link = (
                            child.attrib.get("href", "")
                            or (child.text or "").strip()
                        )

                if not title:
                    continue

                clean_title = re.sub(r"\s+", " ", title).strip()
                key = clean_title.lower()

                if key in seen:
                    continue

                seen.add(key)

                results.append({
                    "source": source,
                    "title": clean_title,
                    "url": link
                })

        except Exception as error:
            print(f"Could not read {source}: {error}")

    # Keep the list manageable
    results = results[:60]

    if not results:
        raise RuntimeError(
            "No creator topics were collected. "
            "Check the internet feeds and try again."
        )

    return results


def save_trends(trends):
    with open(
        OUTPUT_DIR / "trends.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["source", "title", "url"]
        )

        writer.writeheader()
        writer.writerows(trends)


def create_ai_scripts(trends):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from GitHub Secrets."
        )

    topics = "\n".join(
        f"- Source: {item['source']}\n"
        f"  Topic: {item['title']}\n"
        f"  Link: {item['url']}"
        for item in trends
    )

    prompt = f"""
You are the head content creator for TRENDCLIP DAILY.

IMPORTANT:
This is NOT a traditional news channel.

Our channel covers:
- Popular streamers
- TikTok creators
- Viral livestream moments
- Funny internet moments
- Creator reactions
- Creator collaborations
- Public creator disagreements and drama
- Viral challenges and trends
- Gaming and entertainment creators

Your job is to create FIVE entertaining YouTube Shorts scripts
based on the supplied topics.

SOURCE MATERIAL:
{topics}

CONTENT RULES:

1. Prioritize streamer and TikTok culture.
2. Choose the most entertaining and relevant topics.
3. Do not write traditional news reports.
4. Write like an energetic creator talking directly to viewers.
5. Use natural, conversational language.
6. Start with a powerful hook that makes people stop scrolling.
7. Keep each narration around 30-45 seconds.
8. Make the storytelling exciting without exaggerating facts.
9. Never invent quotes, events, or accusations.
10. Do not present rumors as confirmed facts.
11. If a topic lacks enough reliable information, skip it.
12. Do not use fake engagement statistics.
13. Avoid repeating the same topic.
14. Do not write generic news introductions.

STYLE EXAMPLE:

"Bro, you have to see what just happened on stream.
Everybody thought this was going to be a normal livestream,
but then things took a completely unexpected turn..."

This is only an example of tone. Do not copy it repeatedly.

FOR EACH OF THE FIVE SHORTS, USE THIS FORMAT:

### VIDEO 1
Title:
Hook:
[[NARRATION_START]]
Write the complete spoken narration here.
[[NARRATION_END]]

Suggested Visual Scenes:
1.
2.
3.

On-Screen Captions:
1.
2.
3.

Description:
Hashtags:
Source:
Fact Check Note:

Repeat the same format for VIDEO 2 through VIDEO 5.

IMPORTANT OUTPUT REQUIREMENTS:

- Include all five videos.
- Put narration only between the exact narration markers.
- Do not put headings or visual directions inside narration markers.
- Make the first video especially entertaining.
- The narration must be ready for text-to-speech.
- Return plain text, not JSON.
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + MODEL
        + ":generateContent?key="
        + quote(api_key)
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
            "maxOutputTokens": 8000
        }
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Gemini API error {error.code}: {details}"
        )

    except Exception as error:
        raise RuntimeError(f"Gemini request failed: {error}")

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]

    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            "Gemini returned an unexpected response: "
            + json.dumps(data)[:2000]
        )


def extract_narrations(full_text):
    pattern = re.compile(
        r"\[\[NARRATION_START\]\](.*?)"
        r"\[\[NARRATION_END\]\]",
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(full_text)

    return [
        narration.strip()
        for narration in matches
        if narration.strip()
    ]


def main():
    print("===================================")
    print(" TRENDCLIP DAILY")
    print(" STREAMER & TIKTOK CULTURE")
    print("===================================")

    print("\nCollecting creator trends...")

    trends = get_trends()
    save_trends(trends)

    print(f"Collected {len(trends)} topics.")

    print("\nGenerating creator-style scripts...")

    full_scripts = create_ai_scripts(trends)

    # Save all five scripts for reference
    with open(
        OUTPUT_DIR / "all_shorts_scripts.txt",
        "w",
        encoding="utf-8"
    ) as file:
        file.write(full_scripts)

    narrations = extract_narrations(full_scripts)

    if not narrations:
        raise RuntimeError(
            "Gemini did not return narration using the required markers."
        )

    # Keep the first narration in the format expected
    # by the existing video_creator.py
    first_narration = narrations[0]

    narration_file = (
        "TRENDCLIP DAILY - CREATOR CULTURE SHORT\n\n"
        "Original Narration:\n\n"
        + first_narration
        + "\n"
    )

    with open(
        OUTPUT_DIR / "shorts_scripts.txt",
        "w",
        encoding="utf-8"
    ) as file:
        file.write(narration_file)

    # Save a quick list of the collected video ideas
    with open(
        OUTPUT_DIR / "video_ideas.txt",
        "w",
        encoding="utf-8"
    ) as file:
        for number, item in enumerate(trends, start=1):
            file.write(
                f"{number}. {item['title']}\n"
                f"Source: {item['source']}\n"
                f"Link: {item['url']}\n\n"
            )

    print("\nSUCCESS!")
    print(f"Generated {len(narrations)} narration(s).")
    print("First narration saved for video creation.")
    print("All scripts saved in output/all_shorts_scripts.txt")
    print("Ready for video_creator.py!")


if __name__ == "__main__":
    main()
