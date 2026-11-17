
import asyncio
import re
import subprocess
import textwrap
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

OUT = Path("output")
W, H = 1080, 1920
VOICE = "en-US-AriaNeural"


def font(size):
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(path, size)


def get_narration():
    text = (OUT / "shorts_scripts.txt").read_text(encoding="utf-8")

    match = re.search(
        r"Original narration[^\n]*\n(.*?)(?=\n\s*(?:4[.)]|Suggested visual scenes|Visual scenes)|\Z)",
        text,
        re.I | re.S
    )

    if not match:
        raise RuntimeError("Could not find narration in the AI script.")

    narration = re.sub(r"\s+", " ", match.group(1)).strip()

    if len(narration) < 80:
        raise RuntimeError("Narration is too short.")

    return narration


def make_frame(caption, number, total, path):
    image = Image.new("RGB", (W, H), (17, 24, 55))
    draw = ImageDraw.Draw(image)

    draw.ellipse((-200, 150, 450, 800), fill=(45, 65, 130))
    draw.ellipse((700, 1150, 1300, 1750), fill=(20, 100, 120))

    draw.text((85, 130), "TRENDCLIP DAILY", font=font(48), fill="white")
    draw.text((85, 320), "THE INTERNET IS TALKING...",
              font=font(32), fill=(100, 225, 255))

    lines = textwrap.wrap(caption, width=22)
    line_height = 100
    y = (H - len(lines) * line_height) // 2

    for line in lines:
        box = draw.textbbox((0, 0), line, font=font(72))
        x = (W - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=font(72), fill="white")
        y += line_height

    draw.text((85, 1720), "FOLLOW FOR MORE TRENDS",
              font=font(34), fill=(180, 230, 255))

    image.save(path)


async def make_voice(text, path):
    voice = edge_tts.Communicate(
        text,
        VOICE,
        rate="+4%"
    )
    await voice.save(str(path))


def main():
    OUT.mkdir(exist_ok=True)

    narration = get_narration()
    audio = OUT / "voiceover.mp3"

    asyncio.run(make_voice(narration, audio))

    words = narration.split()
    captions = [
        " ".join(words[i:i + 9])
        for i in range(0, len(words), 9)
    ]

    frames = OUT / "video_frames"
    frames.mkdir(exist_ok=True)

    paths = []

    for i, caption in enumerate(captions):
        path = frames / f"frame_{i:03}.png"
        make_frame(caption, i, len(captions), path)
        paths.append(path)

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    duration = float(probe.stdout.strip()) / len(paths)

    concat = OUT / "frames.txt"

    with concat.open("w") as file:
        for path in paths:
            file.write(f"file '{path.resolve()}'\n")
            file.write(f"duration {duration:.4f}\n")
        file.write(f"file '{paths[-1].resolve()}'\n")

    video = OUT / "trendclip_first_short.mp4"

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat),
            "-i", str(audio),
            "-vf", "fps=30,format=yuv420p",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-shortest",
            "-movflags", "+faststart",
            str(video)
        ],
        check=True
    )

    print("SUCCESS: First TrendClip Short created!")
    print(video)


if __name__ == "__main__":
    main()
