
import asyncio
import re
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

OUT = Path("output")
W, H = 1080, 1920
VOICE = "en-US-AriaNeural"


def font(size):
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        size
    )


def get_narration():
    script = (OUT / "shorts_scripts.txt").read_text(
        encoding="utf-8"
    )

    # Find narration even if Gemini changes the heading format.
    patterns = [
        r"(?:original\s+)?narration\s*[:\-]*\s*\n(.*?)(?=\n\s*(?:4[.)]|suggested\s+visual|visual\s+scenes|on-screen\s+captions|description|fact-check)|\Z)",
        r"(?:voiceover|voice-over|spoken\s+script)\s*[:\-]*\s*\n(.*?)(?=\n\s*(?:4[.)]|suggested\s+visual|visual\s+scenes|on-screen\s+captions|description|fact-check)|\Z)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            script,
            re.I | re.S
        )

        if match:
            narration = re.sub(
                r"\s+",
                " ",
                match.group(1)
            ).strip()

            narration = re.sub(
                r"^(?:\d+[.)]\s*)+",
                "",
                narration
            )

            if len(narration) >= 80:
                return narration

    # Fallback: find a numbered narration section.
    lines = script.splitlines()

    for i, line in enumerate(lines):
        if re.search(
            r"\bnarration\b|\bvoiceover\b|\bvoice-over\b",
            line,
            re.I
        ):
            collected = []

            for next_line in lines[i + 1:]:
                if re.match(
                    r"\s*(?:4[.)]|5[.)]|6[.)]|7[.)]|suggested visual|visual scenes|on-screen captions|description|fact-check)",
                    next_line,
                    re.I
                ):
                    break

                if next_line.strip():
                    collected.append(next_line.strip())

            narration = re.sub(
                r"\s+",
                " ",
                " ".join(collected)
            ).strip()

            if len(narration) >= 80:
                return narration

    raise RuntimeError(
        "Could not find narration. "
        "Check output/shorts_scripts.txt for the AI script format."
    )


async def make_voice_and_timing(text, audio_path):
    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate="-5%"
    )

    boundaries = []

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():

            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])

            elif chunk["type"] == "WordBoundary":
                boundaries.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "duration": chunk["duration"] / 10_000_000
                })

    if not boundaries:
        raise RuntimeError(
            "Voice timing information was not received."
        )

    return boundaries


def make_frame(caption, number, total, path):
    image = Image.new("RGB", (W, H))
    pixels = image.load()

    for y in range(H):
        t = y / H
        color = (
            int(8 + 10 * t),
            int(13 + 13 * t),
            int(31 + 31 * t)
        )

        for x in range(W):
            pixels[x, y] = color

    draw = ImageDraw.Draw(image)

    for x in range(0, W, 90):
        draw.line(
            (x, 0, x, H),
            fill=(22, 32, 57),
            width=1
        )

    for y in range(0, H, 90):
        draw.line(
            (0, y, W, y),
            fill=(22, 32, 57),
            width=1
        )

    draw.ellipse(
        (760, 160, 1230, 630),
        fill=(17, 45, 82)
    )

    draw.ellipse(
        (-260, 1300, 330, 1890),
        fill=(13, 53, 70)
    )

    draw.rounded_rectangle(
        (66, 92, 1014, 198),
        radius=34,
        fill=(21, 33, 60),
        outline=(54, 91, 145),
        width=3
    )

    draw.text(
        (105, 119),
        "TRENDCLIP",
        font=font(42),
        fill="white"
    )

    draw.text(
        (420, 128),
        "DAILY",
        font=font(34),
        fill=(75, 220, 255)
    )

    draw.text(
        (82, 300),
        "THE INTERNET IS TALKING",
        font=font(30),
        fill=(105, 205, 235)
    )

    draw.rounded_rectangle(
        (58, 560, 1022, 1350),
        radius=48,
        fill=(17, 27, 51),
        outline=(63, 91, 135),
        width=4
    )

    words = caption.split()
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()

        if len(test) > 19 and current:
            lines.append(current)
            current = word
        else:
            current = test

    if current:
        lines.append(current)

    line_height = 112
    y = 560 + (790 - len(lines) * line_height) // 2

    for line in lines:
        selected_font = font(
            76 if len(line) < 17 else 66
        )

        bounds = draw.textbbox(
            (0, 0),
            line,
            font=selected_font
        )

        x = (W - (bounds[2] - bounds[0])) // 2

        draw.text(
            (x, y),
            line,
            font=selected_font,
            fill="white",
            stroke_width=1,
            stroke_fill=(5, 10, 24)
        )

        y += line_height

    draw.text(
        (82, 1465),
        "TREND ALERT",
        font=font(32),
        fill=(75, 220, 255)
    )

    draw.text(
        (82, 1710),
        "FOLLOW FOR MORE INTERNET TRENDS",
        font=font(29),
        fill=(205, 222, 245)
    )

    left, right, top, bottom = 82, 998, 1800, 1818

    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=9,
        fill=(49, 62, 88)
    )

    progress = int(
        (number + 1) / max(total, 1) * (right - left)
    )

    draw.rounded_rectangle(
        (left, top, left + progress, bottom),
        radius=9,
        fill=(75, 220, 255)
    )

    image.save(path)


def main():
    OUT.mkdir(exist_ok=True)

    narration = get_narration()

    print("Narration found successfully.")
    print("Creating English voiceover...")

    audio = OUT / "voiceover.mp3"

    boundaries = asyncio.run(
        make_voice_and_timing(
            narration,
            audio
        )
    )

    groups = [
        boundaries[i:i + 4]
        for i in range(0, len(boundaries), 4)
    ]

    frames = OUT / "video_frames"
    frames.mkdir(exist_ok=True)

    paths = []

    for index, group in enumerate(groups):
        caption = " ".join(
            item["text"] for item in group
        )

        frame_path = frames / f"frame_{index:03}.png"

        make_frame(
            caption,
            index,
            len(groups),
            frame_path
        )

        paths.append(frame_path)

    probe = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    audio_duration = float(
        probe.stdout.strip()
    )

    concat = OUT / "frames.txt"

    with concat.open(
        "w",
        encoding="utf-8"
    ) as file:

        for index, group in enumerate(groups):
            start = group[0]["start"]

            if index + 1 < len(groups):
                end = groups[index + 1][0]["start"]
            else:
                end = audio_duration

            duration = max(
                0.5,
                end - start
            )

            file.write(
                f"file '{paths[index].resolve()}'\n"
            )

            file.write(
                f"duration {duration:.4f}\n"
            )

        file.write(
            f"file '{paths[-1].resolve()}'\n"
        )

    video = OUT / "trendclip_first_short.mp4"

    print("Rendering synchronized video...")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat),
            "-i", str(audio),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-vf", "format=yuv420p",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-t", str(audio_duration),
            "-fps_mode", "vfr",
            "-movflags", "+faststart",
            str(video)
        ],
        check=True
    )

    print(
        "SUCCESS: Synchronized TrendClip Daily video created!"
    )

    print(video)


if __name__ == "__main__":
    main()
