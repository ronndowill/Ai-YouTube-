
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


# ==================================================
# TRENDCLIP DAILY
# STREAMER & TIKTOK CULTURE AUTOMATION
# ==================================================

MODEL = "gemini-3.5-flash-lite"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 TrendClipDaily/1.0"
}


# ==================================================
# CREATOR TOPIC SEARCHES
# ==================================================

SEARCHES = [
    (
        "Streamer Culture",
        '"Kai Cenat" OR "IShowSpeed" OR "Adin Ross" livestream'
    ),
    (
        "TikTok Creators",
        "TikTok viral creator trends"
    ),
    (
        "Twitch Streamers",
        "Twitch streamer viral moments"
    ),
    (
        "Creator Drama",
        "influencer creator controversy"
    ),
    (
        "Internet Trends",
        "viral internet moments social media"
    ),
    (
        "YouTube Creators",
        "popular YouTube creators viral videos"
    ),
    (
        "Gaming Creators",
        "gaming streamer viral clips"
    ),
    (
        "Creator Reactions",
        "streamer reaction viral video"
    ),
]


# ==================================================
# DOWNLOAD DATA
# ==================================================

def fetch_url(url, timeout=30):

    request = urllib.request.Request(
        url,
        headers=HEADERS
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout
    ) as response:

        return response.read()


# ==================================================
# COLLECT CREATOR TOPICS
# ==================================================

def get_trends():

    results = []
    seen = set()

    for source, search_term in SEARCHES:

        url = (
            "https://news.google.com/rss/search?q="
            + quote(search_term + " when:7d")
            + "&hl=en-US&gl=US&ceid=US:en"
        )

        try:

            print(f"\nChecking {source}...")

            raw = fetch_url(url)

            root = ET.fromstring(raw)

            count = 0

            for item in root.iter():

                tag = item.tag.split("}")[-1]

                if tag != "item":
                    continue

                title = ""
                link = ""
                published = ""

                for child in item:

                    child_tag = child.tag.split("}")[-1]

                    if child_tag == "title":
                        title = (child.text or "").strip()

                    elif child_tag == "link":
                        link = (child.text or "").strip()

                    elif child_tag == "pubDate":
                        published = (child.text or "").strip()

                if not title:
                    continue

                title = re.sub(
                    r"\s+",
                    " ",
                    title
                ).strip()

                key = title.lower()

                if key in seen:
                    continue

                seen.add(key)

                results.append({
                    "source": source,
                    "title": title,
                    "url": link,
                    "published": published
                })

                count += 1

            print(f"Found {count} topics from {source}.")

        except Exception as error:

            print(
                f"Could not collect {source}: {error}"
            )

        time.sleep(1)

    if not results:

        raise RuntimeError(
            "No creator topics were collected. "
            "Google News RSS may be temporarily unavailable."
        )

    print(f"\nTotal topics collected: {len(results)}")

    return results[:60]


# ==================================================
# SAVE TREND DATA
# ==================================================

def save_trends(trends):

    path = OUTPUT_DIR / "trends.csv"

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "source",
                "title",
                "url",
                "published"
            ]
        )

        writer.writeheader()
        writer.writerows(trends)

    print(f"Saved trends: {path}")


# ==================================================
# SAVE VIDEO IDEAS
# ==================================================

def save_video_ideas(trends):

    path = OUTPUT_DIR / "video_ideas.txt"

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        for number, item in enumerate(
            trends,
            start=1
        ):

            file.write(
                f"{number}. {item['title']}\n"
                f"Category: {item['source']}\n"
                f"Published: {item['published']}\n"
                f"Source: {item['url']}\n\n"
            )

    print(f"Saved video ideas: {path}")


# ==================================================
# GENERATE FIVE CREATOR-STYLE SCRIPTS
# ==================================================

def create_ai_scripts(trends):

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY is missing. "
            "Check your GitHub repository Secrets."
        )

    topics = "\n\n".join(
        [
            f"CATEGORY: {item['source']}\n"
            f"TOPIC: {item['title']}\n"
            f"DATE: {item['published']}\n"
            f"SOURCE LINK: {item['url']}"
            for item in trends
        ]
    )

    prompt = f"""
You are the head entertainment content creator
for TRENDCLIP DAILY.

IMPORTANT:
We are NOT a traditional news channel.

We are an entertaining internet culture channel
focused on streamers, TikTok creators and viral moments.

OUR CONTENT CATEGORIES:

1. Popular streamers.
2. TikTok stars and creators.
3. Twitch livestream moments.
4. Funny internet moments.
5. Creator reactions.
6. Public creator disagreements and drama.
7. Viral challenges.
8. Gaming creators.
9. YouTube personalities.
10. Unexpected internet moments.

CURRENT TOPIC RESEARCH:

{topics}

YOUR ASSIGNMENT:

Create FIVE different YouTube Shorts scripts
using the most interesting available topics.

STYLE:

Write like an entertaining social media commentator.

The narration should sound like someone talking
directly to their audience.

Use:
- Energetic storytelling.
- Natural conversational language.
- Strong opening hooks.
- Short, punchy sentences.
- Interesting details.
- Fast-paced storytelling.
- Memorable endings.

DO NOT:
- Sound like a television news reporter.
- Start with "Good morning" or "Breaking news."
- Use boring introductions.
- Invent quotes or events.
- Make unsupported accusations.
- Present rumors as confirmed facts.
- Pretend you watched a livestream or video.
- Invent view counts or engagement numbers.
- Repeat the same story in multiple videos.

ACCURACY:

Use only information supported by the supplied
source material.

If a topic does not have enough information,
choose another topic.

Clearly distinguish allegations from confirmed facts.

VIDEO LENGTH:

Aim for approximately 30 to 45 seconds
of spoken narration per video.

REQUIRED OUTPUT FORMAT:

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


Repeat this exact format for:

VIDEO 2
VIDEO 3
VIDEO 4
VIDEO 5

FINAL INSTRUCTIONS:

- Generate five different videos.
- Make VIDEO 1 the strongest.
- Prioritize streamer and TikTok culture.
- Keep the scripts entertaining and conversational.
- Put ONLY spoken words inside narration markers.
- Keep visual suggestions outside narration markers.
- Make narration ready for text-to-speech.
- Include the source link when available.
- Return plain text, not JSON.
"""

    api_url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        + MODEL
        + ":generateContent?key="
        + quote(api_key)
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
            "temperature": 0.85,
            "maxOutputTokens": 8000
        }
    }

    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:

        print("\nSending topics to Gemini...")

        with urllib.request.urlopen(
            request,
            timeout=180
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:

        details = error.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"Gemini API error {error.code}: {details}"
        )

    except Exception as error:

        raise RuntimeError(
            f"Gemini request failed: {error}"
        )

    try:

        parts = data["candidates"][0]["content"]["parts"]

        generated_text = "\n".join(
            part.get("text", "")
            for part in parts
            if part.get("text")
        )

        if not generated_text.strip():

            raise RuntimeError(
                "Gemini returned empty script content."
            )

        return generated_text

    except (KeyError, IndexError, TypeError):

        raise RuntimeError(
            "Unexpected Gemini response: "
            + json.dumps(data)[:3000]
        )


# ==================================================
# EXTRACT NARRATIONS
# ==================================================

def extract_narrations(full_text):

    pattern = re.compile(
        r"\[\[NARRATION_START\]\]"
        r"(.*?)"
        r"\[\[NARRATION_END\]\]",
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(full_text)

    narrations = []

    for match in matches:

        narration = match.strip()

        if narration:

            narrations.append(narration)

    return narrations


# ==================================================
# SAVE ALL FIVE SCRIPTS
# ==================================================

def save_all_scripts(full_scripts):

    path = OUTPUT_DIR / "all_shorts_scripts.txt"

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(full_scripts)

    print(f"Saved complete scripts: {path}")


# ==================================================
# SAVE FIRST NARRATION FOR VIDEO GENERATOR
# ==================================================

def save_first_narration(narrations):

    if not narrations:

        raise RuntimeError(
            "No narration was found in Gemini's response."
        )

    first_narration = narrations[0]

    if len(first_narration) < 40:

        raise RuntimeError(
            "The first narration is too short. "
            "Please check Gemini's generated response."
        )

    content = (
        "TRENDCLIP DAILY - CREATOR CULTURE SHORT\n\n"
        "Original Narration:\n\n"
        + first_narration
        + "\n"
    )

    path = OUTPUT_DIR / "shorts_scripts.txt"

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(content)

    print(f"Saved first narration: {path}")

    return first_narration


# ==================================================
# MAIN AUTOMATION
# ==================================================

def main():

    print("\n")
    print("==========================================")
    print("          TRENDCLIP DAILY")
    print("     STREAMER & TIKTOK CULTURE")
    print("==========================================")

    print("\nSTEP 1: Collecting creator topics...")

    trends = get_trends()

    save_trends(trends)
    save_video_ideas(trends)

    print("\nSTEP 2: Generating five video scripts...")

    full_scripts = create_ai_scripts(trends)

    save_all_scripts(full_scripts)

    print("\nSTEP 3: Extracting narration...")

    narrations = extract_narrations(full_scripts)

    print(
        f"Successfully extracted {len(narrations)} narration(s)."
    )

    if len(narrations) < 5:

        print(
            "WARNING: Gemini returned fewer than five "
            "complete narrations."
        )

    print("\nSTEP 4: Preparing video generator...")

    save_first_narration(narrations)

    print("\n==========================================")
    print("             SUCCESS!")
    print("==========================================")

    print("Creator topics collected.")
    print("AI scripts generated.")
    print("First narration prepared.")
    print("Ready for video_creator.py.")

    print("\nOUTPUT FILES:")

    print("- output/trends.csv")
    print("- output/video_ideas.txt")
    print("- output/all_shorts_scripts.txt")
    print("- output/shorts_scripts.txt")

    print("\nTRENDCLIP DAILY AUTOMATION COMPLETE!")


# ==================================================
# START PROGRAM
# ==================================================

if __name__ == "__main__":

    main()
