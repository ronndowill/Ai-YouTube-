
import csv
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

FEEDS = [
    ("Google Trends US", "https://trends.google.com/trending/rss?geo=US"),
    ("Reddit Popular", "https://www.reddit.com/r/popular/.rss"),
]

def get_trends():
    results = []
    for source, url in FEEDS:
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "TrendClipDaily/1.0"}
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                root = ET.fromstring(response.read())

            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                if title:
                    results.append([source, title, link])

            ns = {"a": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//a:entry", ns):
                title = (entry.findtext("a:title", default="", namespaces=ns)).strip()
                link_node = entry.find("a:link", ns)
                link = link_node.get("href", "") if link_node is not None else ""
                if title:
                    results.append([source, title, link])

            print(source, "checked successfully")
        except Exception as error:
            print(source, "could not be checked:", error)

    unique = {}
    for source, title, link in results:
        unique.setdefault(title.lower(), [source, title, link])
    return list(unique.values())

def main():
    print("TRENDCLIP DAILY")
    print("Trend research:", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    trends = get_trends()
    Path("output").mkdir(exist_ok=True)

    with open("output/trends.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Source", "Trending Topic", "Link"])
        writer.writerows(trends)

    with open("output/video_ideas.txt", "w", encoding="utf-8") as file:
        file.write("TRENDCLIP DAILY - VIDEO IDEAS\n\n")
        file.write("Research leads only: verify facts before publishing.\n\n")
        for number, (source, title, link) in enumerate(trends[:20], 1):
            file.write(f"{number}. {title}\n")
            file.write(f"Source: {source}\nLink: {link}\n")
            file.write("Hook: What is everyone talking about?\n")
            file.write("Story: Explain the topic using verified facts.\n")
            file.write("Commentary: Add original insight.\n")
            file.write("Ending: Ask viewers what they think.\n\n")

    print("Topics collected:", len(trends))
    for number, trend in enumerate(trends[:10], 1):
        print(f"{number}. {trend[1]}")
    print("Results saved in output/")

if __name__ == "__main__":
    main()
