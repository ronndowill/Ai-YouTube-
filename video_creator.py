
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

    patterns = [
        r"(?:original\s+)?narration\s*[:\-]*\s*\n(.*?)(?=\n\s*(?:4[.)]|suggested\s+visual|visual scenes|on-screen captions|description|fact-check)|\Z)",
        r"(?:voiceover|voice-over|spoken script)\s*[:\-]*\s*\n(.*?)(?=\n\s*(?:4[.)]|suggested visual|visual scenes|on-screen captions|description|fact-check)|\Z)",
    ]

    for pattern in patterns:
        match = re.search(pattern, script, re.I | re.S)

        if match:
            narration = re.sub(
                r"\s+", " ", match.group(1)
            ).strip()

            narration = re.sub(
                r"^(?:\d+[.)]\s*)+",
                "",
                narration
            )

            if len(narration) >= 80:
                return narration

    raise RuntimeError(
        "Could not find narration in shorts_scripts.txt"
    )


def split_captions(text, max_words=5):
    words = text.split()
    groups = []
    current = []

    for word in words:
        current.append(word)

        if len(current) >= max_words:
            groups.append(" ".join(current))
            current = []

    if current:
        groups.append(" ".join(current))

    return groups


def syllable_weight(text):
    words = re.findall(r"[A-Za-z']+", text)
    total = 0

    for word in words:
        clean = word.lower()
        groups = re.findall(r"[aeiouy]+", clean)
        count = max(1, len(groups))

        if clean.endswith("e") and count > 1:
            count -= 1

        total += count

    return max(total, 1)


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


async def create_voice(text, audio_path):
    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate="-5%"
    )

    await communicate.save(str(audio_path))


def get_audio_duration(audio_path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    return float(result.stdout.strip())


def main():
    OUT.mkdir(exist_ok=True)

    narration = get_narration()

    print("Narration found successfully.")
    print("Creating English voiceover...")

    audio = OUT / "voiceover.mp3"

    asyncio.run(
        create_voice(narration, audio)
    )

    if not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError("Voiceover audio was not created.")

    print("Voiceover saved successfully.")

    audio_duration = get_audio_duration(audio)

    if audio_duration <= 0:
        raise RuntimeError("Audio duration could not be measured.")

    groups = split_captions(narration)

    if not groups:
        raise RuntimeError("No caption groups were created.")

    weights = [syllable_weight(group) for group in groups]
    total_weight = sum(weights)

    frames = OUT / "video_frames"

    frames.mkdir(exist_ok=True)

    paths = []

    for index, caption in enumerate(groups):
        frame_path = frames / f"frame_{index:03}.png"

        make_frame(
            caption,
            index,
            len(groups),
            frame_path
        )

        paths.append(frame_path)

    concat = OUT / "frames.txt"

    with concat.open("w", encoding="utf-8") as file:
        for index, path in enumerate(paths):
            duration = (
                audio_duration
                * weights[index]
                / total_weight
            )

            file.write(
                f"file '{path.resolve()}'\n"
            )

            file.write(
                f"duration {duration:.4f}\n"
            )

        file.write(
            f"file '{paths[-1].resolve()}'\n"
        )

    video = OUT / "trendclip_first_short.mp4"

    print("Rendering TrendClip Daily video...")

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
            "-vf", "fps=30,format=yuv420p",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(audio_duration),
            "-shortest",
            "-movflags", "+faststart",
            str(video)
        ],
        check=True
    )

    if not video.exists() or video.stat().st_size == 0:
        raise RuntimeError("The final video was not created.")

    print("SUCCESS: TrendClip Daily video created!")
    print(video)


if __name__ == "__main__":
    main()
