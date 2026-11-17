
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

MAX_GEMINI_ATTEMPTS = 4
RETRY_DELAYS = [8, 16, 32]


# ==================================================
# CREATOR TOPIC SEARCHES
# ==================================================

SEARCHES = [
    ("Streamer Culture",
     '"Kai Cenat" OR "IShowSpeed" OR "Adin Ross" livestream'),

    ("TikTok Creators",
     "TikTok viral creator trends"),

    ("Twitch Streamers",
     "Twitch streamer viral moments"),

    ("Creator Drama",
     "influencer creator controversy"),

    ("Internet Trends",
     "viral internet moments social media"),

    ("YouTube Creators",
     "popular YouTube creators viral videos"),

    ("Gaming Creators",
     "gaming streamer viral clips"),

    ("Creator Reactions",
     "streamer reaction viral video"),
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

                if item.tag.split("}")[-1] != "item":
                    continue

                title = ""
                link = ""
                published = ""

                for child in item:

                    tag = child.tag.split("}")[-1]

                    if tag == "title":
                        title = (child.text or "").strip()

                    elif tag == "link":
                        link = (child.text or "").strip()

                    elif tag == "pubDate":
                        published = (child.text or "").strip()

                if not title:
                    continue

                title = re.sub(r"\s+", " ", title).strip()

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

            print(f"Could not collect {source}: {error}")

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

        for number, item in enumerate(trends, start=1):

            file.write(
                f"{number}. {item['title']}\n"
                f"Category: {item['source']}\n"
                f"Published: {item['published']}\n"
                f"Source: {item['url']}\n\n"
            )

    print(f"Saved video ideas: {path}")


# ==================================================
# BACKUP SCRIPT GENERATOR
# Works without Gemini or another paid API
# ==================================================

def create_backup_scripts(trends):

    print("\nUsing local backup script generator...")

    scripts = []

    selected = trends[:5]

    if not selected:
        raise RuntimeError("No topics available for backup scripts.")

    for number, item in enumerate(selected, start=1):

        title = item["title"]
        category = item["source"]
        source_url = item["url"]

        narration = (
            f"Here's a creator story getting attention right now. "
            f"The topic is: {title}. "
            f"And this is exactly the kind of internet conversation "
            f"that gets people talking. "
            f"But before jumping to conclusions, it's important to "
            f"separate what's actually reported from what people are "
            f"saying online. "
            f"The headline gives us the subject, but the full story "
            f"deserves a closer look. "
            f"So what do you think about this one? "
            f"Is this something worth paying attention to, "
            f"or will the internet move on to the next big story? "
            f"Let us know what you think in the comments, "
            f"and follow TrendClip Daily for more creator culture."
        )

        script = f"""
### VIDEO {number}

Title: {title}

Hook: The internet has another creator story to talk about!

[[NARRATION_START]]
{narration}
[[NARRATION_END]]

Suggested Visual Scenes:
1. Fast opening text introducing the topic.
2. Creator-related background footage or licensed visuals.
3. Headline-style topic display.
4. Animated question and comment prompt.

On-Screen Captions:
1. THE INTERNET IS TALKING
2. CREATOR CULTURE
3. WHAT DO YOU THINK?
4. FOLLOW FOR MORE

Description:
A creator culture topic worth discussing. Check the original source for full context.

Hashtags:
#TrendClipDaily #Streamer #TikTok #CreatorNews #YouTubeShorts

Source:
{source_url}

Fact Check Note:
Backup script based on the supplied headline only. Verify the original source before publishing.
"""

        scripts.append(script.strip())

    return "\n\n".join(scripts)


# ==================================================
# GEMINI SCRIPT GENERATOR
# ==================================================

def create_ai_scripts(trends):

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:

        print("Gemini API key missing. Using backup scripts.")
        return create_backup_scripts(trends)

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

We are an entertaining internet culture channel
focused on streamers, TikTok creators and viral moments.

CURRENT TOPIC RESEARCH:

{topics}

Create FIVE different YouTube Shorts scripts.

STYLE:
- Energetic social media commentator.
- Strong opening hooks.
- Natural conversational language.
- Short, punchy sentences.
- Fast-paced storytelling.
- Interesting endings.
- Aim for 30 to 45 seconds of narration.

DO NOT:
- Sound like a television news reporter.
- Invent quotes, events or statistics.
- Make unsupported accusations.
- Present rumors as confirmed facts.
- Pretend you watched a video or livestream.
- Repeat the same story.

ACCURACY:
Use only details supported by the supplied sources.
If a headline does not provide enough detail,
do not invent the missing information.
Clearly distinguish allegations from confirmed facts.

REQUIRED OUTPUT FORMAT:

### VIDEO 1

Title:

Hook:

[[NARRATION_START]]
Complete spoken narration here.
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

Repeat this exact format for VIDEO 2 through VIDEO 5.

Make VIDEO 1 the strongest.
Return plain text, not JSON.
Put only spoken words inside narration markers.
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

    for attempt in range(1, MAX_GEMINI_ATTEMPTS + 1):

        try:

            print(
                f"\nSending topics to Gemini "
                f"(attempt {attempt}/{MAX_GEMINI_ATTEMPTS})..."
            )

            with urllib.request.urlopen(
                request,
                timeout=180
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

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

            print("Gemini successfully generated scripts.")

            return generated_text

        except urllib.error.HTTPError as error:

            details = error.read().decode(
                "utf-8",
                errors="replace"
            )

            retryable = error.code in (
                429, 500, 502, 503, 504
            )

            print(
                f"Gemini HTTP error {error.code}: "
                f"{details[:500]}"
            )

            if retryable and attempt < MAX_GEMINI_ATTEMPTS:

                delay = RETRY_DELAYS[attempt - 1]

                print(
                    f"Gemini is temporarily unavailable. "
                    f"Retrying in {delay} seconds..."
                )

                time.sleep(delay)
                continue

            print("Gemini did not recover.")

            break

        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError
        ) as error:

            print(f"Gemini connection problem: {error}")

            if attempt < MAX_GEMINI_ATTEMPTS:

                delay = RETRY_DELAYS[attempt - 1]

                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                continue

            break

        except Exception as error:

            print(f"Gemini response problem: {error}")
            break

    print(
        "\nWARNING: Gemini could not generate scripts. "
        "Switching to local backup mode."
    )

    return create_backup_scripts(trends)


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

    return [
        match.strip()
        for match in matches
        if match.strip()
    ]


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
            "No narration was found in the generated scripts."
        )

    first_narration = narrations[0]

    if len(first_narration) < 40:

        raise RuntimeError(
            "The first narration is too short."
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

    print("\nSTEP 3: Extracting narrations...")

    narrations = extract_narrations(full_scripts)

    print(
        f"Successfully extracted "
        f"{len(narrations)} narration(s)."
    )

    if len(narrations) < 5:

        print(
            "WARNING: Fewer than five narrations "
            "were generated."
        )

    print("\nSTEP 4: Preparing video generator...")

    save_first_narration(narrations)

    print("\n==========================================")
    print("             SUCCESS!")
    print("==========================================")

    print("Creator topics collected.")
    print("Scripts generated or backup scripts prepared.")
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
