
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
        re.I | re.S,
    )

    if not match:
        raise RuntimeError("Could not find narration in the AI script.")

    narration = re.sub(r"\s+", " ", match.group(1)).strip()

    if len(narration) < 80:
        raise RuntimeError("Narration is too short.")

    return narration


def make_frame(caption, number, total, path):
    image = Image.new("RGB", (W, H))
    pixels = image.load()

    # Modern dark gradient
    for y in range(H):
        t = y / H
        color = (
            int(8 + 10 * t),
            int(13 + 13 * t),
            int(31 + 31 * t),
        )
        for x in range(W):
            pixels[x, y] = color

    draw = ImageDraw.Draw(image)

    # Background grid
    for x in range(0, W, 90):
        draw.line((x, 0, x, H), fill=(22, 32, 57), width=1)

    for y in range(0, H, 90):
        draw.line((0, y, W, y), fill=(22, 32, 57), width=1)

    draw.ellipse((760, 160, 1230, 630), fill=(17, 45, 82))
    draw.ellipse((-260, 1300, 330, 1890), fill=(13, 53, 70))

    # Channel branding
    draw.rounded_rectangle(
        (66, 92, 1014, 198),
        radius=34,
        fill=(21, 33, 60),
        outline=(54, 91, 145),
        width=3,
    )

    draw.text((105, 119), "TRENDCLIP", font=font(42), fill="white")
    draw.text((420, 128), "DAILY", font=font(34), fill=(75, 220, 255))

    draw.text(
        (82, 300),
        "THE INTERNET IS TALKING",
        font=font(30),
        fill=(105, 205, 235),
    )

    # Main caption panel
    draw.rounded_rectangle(
        (58, 560, 1022, 1350),
        radius=48,
        fill=(17, 27, 51),
        outline=(63, 91, 135),
        width=4,
    )

    words = caption.split()

    main_text = " ".join(words[:-1]) if len(words) > 1 else ""
    accent = words[-1] if words else ""

    lines = textwrap.wrap(main_text, width=19) if main_text else []

    if accent:
        lines.append(accent)

    line_height = 112
    y = 560 + (790 - len(lines) * line_height) // 2

    for index, line in enumerate(lines):
        selected_font = font(76 if len(line) < 17 else 66)

        bounds = draw.textbbox((0, 0), line, font=selected_font)
        x = (W - (bounds[2] - bounds[0])) // 2

        color = (
            (75, 220, 255)
            if index == len(lines) - 1
            else "white"
        )

        draw.text(
            (x, y),
            line,
            font=selected_font,
            fill=color,
            stroke_width=1,
            stroke_fill=(5, 10, 24),
        )

        y += line_height

    draw.text(
        (82, 1465),
        "TREND ALERT",
        font=font(32),
        fill=(75, 220, 255),
    )

    draw.text(
        (82, 1710),
        "FOLLOW FOR MORE INTERNET TRENDS",
        font=font(29),
        fill=(205, 222, 245),
    )

    # Progress bar
    left, right, top, bottom = 82, 998, 1800, 1818

    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=9,
        fill=(49, 62, 88),
    )

    progress = int(
        (number + 1) / max(total, 1) * (right - left)
    )

    draw.rounded_rectangle(
        (left, top, left + progress, bottom),
        radius=9,
        fill=(75, 220, 255),
    )

    image.save(path)


async def make_voice(text, path):
    voice = edge_tts.Communicate(
        text,
        VOICE,
        rate="+4%",
    )

    await voice.save(str(path))


def main():
    OUT.mkdir(exist_ok=True)

    narration = get_narration()
    audio = OUT / "voiceover.mp3"

    asyncio.run(make_voice(narration, audio))

    words = narration.split()

    captions = [
        " ".join(words[i:i + 7])
        for i in range(0, len(words), 7)
    ]

    frames = OUT / "video_frames"
    frames.mkdir(exist_ok=True)

    paths = []

    for index, caption in enumerate(captions):
        frame_path = frames / f"frame_{index:03}.png"

        make_frame(
            caption,
            index,
            len(captions),
            frame_path,
        )

        paths.append(frame_path)

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    duration = float(probe.stdout.strip()) / len(paths)

    concat = OUT / "frames.txt"

    with concat.open("w", encoding="utf-8") as file:
        for frame_path in paths:
            file.write(f"file '{frame_path.resolve()}'\n")
            file.write(f"duration {duration:.4f}\n")

        file.write(f"file '{paths[-1].resolve()}'\n")

    video = OUT / "trendclip_first_short.mp4"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat),
            "-i",
            str(audio),
            "-vf",
            "zoompan=z='min(zoom+0.00035,1.06)':d=1:s=1080x1920:fps=30,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(video),
        ],
        check=True,
    )

    print("SUCCESS: Updated TrendClip Daily Short created!")
    print(video)


if __name__ == "__main__":
    main()
