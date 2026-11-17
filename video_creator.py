
import asyncio
import math
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ==========================================
# TRENDCLIP AI - YOUTUBE SHORTS EDITION
# ==========================================

OUT = Path("output")
FRAMES = OUT / "video_frames"

W, H = 1080, 1920
FPS = 30

VOICE = "en-US-AriaNeural"
VIDEO_NAME = "trendclip_first_short.mp4"

CAPTION_WORDS = 3
VOICE_RATE = "+5%"

YELLOW = (255, 220, 40)
WHITE = (255, 255, 255)
CYAN = (55, 220, 255)
DARK = (5, 8, 19)

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]

# ==========================================
# FONT
# ==========================================

def font(size):
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# ==========================================
# NARRATION EXTRACTION
# ==========================================

def get_narration():
    possible_files = [
        OUT / "shorts_scripts.txt",
        Path("shorts_scripts.txt"),
    ]

    script_path = next(
        (p for p in possible_files if p.exists()),
        None
    )

    if script_path is None:
        raise FileNotFoundError(
            "Could not find shorts_scripts.txt"
        )

    script = script_path.read_text(
        encoding="utf-8"
    ).strip()

    if not script:
        raise RuntimeError("Script is empty.")

    start_pattern = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?:\*\*)?"
        r"(?:\d+[.)]\s*)?"
        r"(?:original\s+)?"
        r"(?:narration|voice[- ]?over|voiceover|spoken script)"
        r"(?:\*\*)?\s*[:\-–—]?\s*(.*)$",
        re.I
    )

    stop_pattern = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?:\*\*)?"
        r"(?:\d+[.)]\s*)?"
        r"(?:three suggested visual scenes|"
        r"suggested visual scenes|"
        r"three visual scenes|visual scenes|"
        r"short on-screen captions|"
        r"on-screen captions|"
        r"suggested visuals|visual suggestions|"
        r"captions|description|fact-check|hashtags|tags)"
        r"(?:\*\*)?\s*[:\-–—]?\s*$",
        re.I
    )

    lines = script.splitlines()

    start_index = None
    first_line = ""

    for i, line in enumerate(lines):
        match = start_pattern.match(line)

        if match:
            start_index = i
            first_line = match.group(1).strip()
            break

    if start_index is None:
        raise RuntimeError(
            "Could not find Original Narration or Voiceover heading."
        )

    narration_lines = []

    if first_line:
        narration_lines.append(first_line)

    for line in lines[start_index + 1:]:
        if stop_pattern.match(line):
            break

        narration_lines.append(line)

    narration = " ".join(narration_lines)

    narration = re.sub(r"\s+", " ", narration)
    narration = re.sub(r"\*\*|__|`", "", narration)
    narration = re.sub(r"^(?:\d+[.)]\s*)+", "", narration)

    narration = narration.strip()

    if len(narration) < 80:
        raise RuntimeError(
            "Narration is too short or could not be extracted."
        )

    return narration


# ==========================================
# CAPTION GENERATION
# ==========================================

def split_captions(text, max_words=CAPTION_WORDS):
    words = text.split()
    groups = []

    current = []

    for word in words:
        current.append(word)

        if len(current) >= max_words:
            groups.append(current)
            current = []

    if current:
        groups.append(current)

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


# ==========================================
# BACKGROUND DESIGN
# ==========================================

def create_background(number):
    image = Image.new("RGB", (W, H))
    pixels = image.load()

    top = (5, 8, 22)
    bottom = (17, 18, 52)

    for y in range(H):
        t = y / H

        color = tuple(
            int(top[c] * (1 - t) + bottom[c] * t)
            for c in range(3)
        )

        for x in range(W):
            pixels[x, y] = color

    draw = ImageDraw.Draw(image)

    # Decorative glowing circles.
    for i in range(7):
        x = (i * 193 + number * 71) % W
        y = (i * 307 + number * 113) % H
        radius = 100 + (i % 3) * 40

        draw.ellipse(
            (
                x - radius,
                y - radius,
                x + radius,
                y + radius
            ),
            outline=(20, 38, 83),
            width=3
        )

    # Diagonal decorative lines.
    for i in range(-H, W, 180):
        draw.line(
            (i, 0, i + H, H),
            fill=(17, 29, 57),
            width=2
        )

    return image


# ==========================================
# TEXT HELPERS
# ==========================================

def text_width(draw, text, selected_font):
    box = draw.textbbox(
        (0, 0),
        text,
        font=selected_font,
        stroke_width=0
    )

    return box[2] - box[0]


def fit_font(draw, text, starting_size, maximum_width):
    size = starting_size

    while size > 42:
        selected = font(size)

        if text_width(draw, text, selected) <= maximum_width:
            return selected

        size -= 4

    return font(42)


# ==========================================
# SHORTS FRAME DESIGN
# ==========================================

def make_frame(words, number, total, path):
    image = create_background(number)
    draw = ImageDraw.Draw(image)

    # Top branding.
    draw.rounded_rectangle(
        (65, 95, 1015, 205),
        radius=38,
        fill=(14, 23, 48),
        outline=(43, 77, 126),
        width=3
    )

    draw.text(
        (105, 124),
        "TRENDCLIP",
        font=font(43),
        fill=WHITE
    )

    draw.text(
        (420, 133),
        "AI",
        font=font(36),
        fill=YELLOW
    )

    # Small live label.
    draw.rounded_rectangle(
        (760, 123, 960, 175),
        radius=18,
        fill=(139, 30, 42)
    )

    draw.ellipse(
        (780, 140, 798, 158),
        fill=(255, 75, 75)
    )

    draw.text(
        (810, 128),
        "TRENDING",
        font=font(23),
        fill=WHITE
    )

    # Main visual panel.
    draw.rounded_rectangle(
        (65, 510, 1015, 1325),
        radius=48,
        fill=(10, 17, 37),
        outline=(39, 65, 111),
        width=4
    )

    # Caption label.
    draw.text(
        (105, 585),
        "WATCH THIS",
        font=font(28),
        fill=CYAN
    )

    # Main caption.
    caption = " ".join(words).upper()

    selected_font = fit_font(
        draw,
        caption,
        112,
        820
    )

    box = draw.textbbox(
        (0, 0),
        caption,
        font=selected_font,
        stroke_width=3
    )

    caption_width = box[2] - box[0]
    caption_height = box[3] - box[1]

    x = (W - caption_width) // 2
    y = 900 - caption_height // 2

    # Shadow.
    draw.text(
        (x + 7, y + 9),
        caption,
        font=selected_font,
        fill=(0, 0, 0),
        stroke_width=5,
        stroke_fill=(0, 0, 0)
    )

    # White caption.
    draw.text(
        (x, y),
        caption,
        font=selected_font,
        fill=WHITE,
        stroke_width=3,
        stroke_fill=(0, 0, 0)
    )

    # Highlight final word.
    last_word = words[-1].upper()

    highlight_font = fit_font(
        draw,
        last_word,
        100,
        820
    )

    highlight_width = text_width(
        draw,
        last_word,
        highlight_font
    )

    draw.rounded_rectangle(
        (
            (W - highlight_width) // 2 - 25,
            1080,
            (W + highlight_width) // 2 + 25,
            1200
        ),
        radius=20,
        fill=(49, 40, 9)
    )

    draw.text(
        ((W - highlight_width) // 2, 1085),
        last_word,
        font=highlight_font,
        fill=YELLOW,
        stroke_width=2,
        stroke_fill=(0, 0, 0)
    )

    # Bottom callout.
    draw.text(
        (85, 1450),
        "DON'T SCROLL!",
        font=font(43),
        fill=YELLOW
    )

    draw.text(
        (85, 1525),
        "MORE STORIES. MORE TRENDS.",
        font=font(27),
        fill=WHITE
    )

    # Progress bar.
    left = 80
    right = 1000
    top = 1790
    bottom = 1812

    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=12,
        fill=(45, 52, 75)
    )

    progress = int(
        (number + 1) / max(total, 1) * (right - left)
    )

    draw.rounded_rectangle(
        (left, top, left + progress, bottom),
        radius=12,
        fill=YELLOW
    )

    # Frame number.
    draw.text(
        (850, 1720),
        f"{number + 1}/{total}",
        font=font(25),
        fill=(165, 190, 220)
    )

    image.save(path, optimize=True)


# ==========================================
# VOICE GENERATION
# ==========================================

async def create_voice(text, audio_path):
    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate=VOICE_RATE
    )

    await communicate.save(str(audio_path))


# ==========================================
# AUDIO DURATION
# ==========================================

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


# ==========================================
# REQUIREMENTS
# ==========================================

def check_requirements():
    for program in ("ffmpeg", "ffprobe"):
        if shutil.which(program) is None:
            raise RuntimeError(
                f"{program} is not installed."
            )


# ==========================================
# VIDEO RENDERING
# ==========================================

def render_video(concat_file, audio, video, duration):
    command = [
        "ffmpeg",
        "-y",

        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),

        "-i", str(audio),

        "-map", "0:v:0",
        "-map", "1:a:0",

        "-vf",
        (
            "fps=30,"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "zoompan="
            "z='min(zoom+0.00035,1.045)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            "d=1:s=1080x1920:fps=30,"
            "setsar=1,"
            "format=yuv420p"
        ),

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "21",

        "-c:a", "aac",
        "-b:a", "160k",

        "-t", str(duration),
        "-shortest",

        "-movflags", "+faststart",

        str(video)
    ]

    subprocess.run(command, check=True)


# ==========================================
# MAIN GENERATOR
# ==========================================

def main():
    print("")
    print("======================================")
    print("       TRENDCLIP AI SHORTS")
    print("       NEW VIDEO GENERATOR")
    print("======================================")

    OUT.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)

    check_requirements()

    # Read narration.
    print("\n[1/6] Reading narration...")

    narration = get_narration()

    print("Narration loaded.")
    print("Characters:", len(narration))

    # Create audio.
    print("\n[2/6] Creating AI voiceover...")

    audio = OUT / "voiceover.mp3"

    asyncio.run(
        create_voice(narration, audio)
    )

    if not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError("Voiceover generation failed.")

    duration = get_audio_duration(audio)

    if duration <= 0:
        raise RuntimeError("Invalid audio duration.")

    print(f"Audio duration: {duration:.2f} seconds")

    # Split captions.
    print("\n[3/6] Creating animated captions...")

    groups = split_captions(narration)

    if not groups:
        raise RuntimeError("No captions created.")

    weights = [
        syllable_weight(" ".join(group))
        for group in groups
    ]

    total_weight = sum(weights)

    # Generate images.
    print("\n[4/6] Designing Shorts visuals...")

    for old in FRAMES.glob("frame_*.png"):
        old.unlink()

    paths = []

    for index, words in enumerate(groups):
        frame_path = FRAMES / f"frame_{index:04d}.png"

        make_frame(
            words,
            index,
            len(groups),
            frame_path
        )

        paths.append(frame_path)

        print(
            f"Created frame {index + 1}/{len(groups)}"
        )

    if not paths:
        raise RuntimeError("No frames generated.")

    # Create concat instructions.
    print("\n[5/6] Preparing video timeline...")

    concat_file = OUT / "frames.txt"

    with concat_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        for index, path in enumerate(paths):
            segment_duration = (
                duration * weights[index] / total_weight
            )

            file.write(
                f"file '{path.resolve()}'\n"
            )

            file.write(
                f"duration {segment_duration:.5f}\n"
            )

        file.write(
            f"file '{paths[-1].resolve()}'\n"
        )

    # Render.
    print("\n[6/6] Rendering final YouTube Short...")

    video = OUT / VIDEO_NAME

    render_video(
        concat_file,
        audio,
        video,
        duration
    )

    # Verify.
    if not video.exists() or video.stat().st_size == 0:
        raise RuntimeError("Final video was not created.")

    size_mb = video.stat().st_size / (1024 * 1024)

    print("")
    print("======================================")
    print("          VIDEO COMPLETE!")
    print("======================================")
    print("File:", video)
    print("Duration:", round(duration, 2), "seconds")
    print("Caption scenes:", len(groups))
    print("Resolution: 1080 x 1920")
    print("FPS:", FPS)
    print("File size:", round(size_mb, 2), "MB")
    print("======================================")


if __name__ == "__main__":
    main()
