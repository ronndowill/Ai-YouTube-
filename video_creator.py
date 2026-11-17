
import asyncio
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# TRENDCLIP DAILY SETTINGS
# ==========================================

OUT = Path("output")
W, H = 1080, 1920
VOICE = "en-US-AriaNeural"
VIDEO_NAME = "trendclip_first_short.mp4"

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]


# ==========================================
# FONT
# ==========================================

def font(size):
    for font_path in FONT_PATHS:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size)

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
        (path for path in possible_files if path.exists()),
        None
    )

    if script_path is None:
        raise FileNotFoundError(
            "Could not find shorts_scripts.txt. "
            "Check that Main.py creates the file before "
            "video_creator.py runs."
        )

    script = script_path.read_text(
        encoding="utf-8"
    ).strip()

    if not script:
        raise RuntimeError(
            "shorts_scripts.txt is empty."
        )

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
        r"suggested visuals|"
        r"visual suggestions|"
        r"captions|"
        r"description|"
        r"fact-check|"
        r"hashtags|"
        r"tags)"
        r"(?:\*\*)?\s*[:\-–—]?\s*$",
        re.I
    )

    lines = script.splitlines()
    start_index = None
    first_line = ""

    for index, line in enumerate(lines):
        match = start_pattern.match(line)

        if match:
            start_index = index
            first_line = match.group(1).strip()
            break

    if start_index is None:
        raise RuntimeError(
            "Could not find a narration heading in "
            "shorts_scripts.txt. Expected a heading such as "
            "'Original Narration' or 'Voiceover'."
        )

    narration_lines = []

    if first_line:
        narration_lines.append(first_line)

    for line in lines[start_index + 1:]:
        if stop_pattern.match(line):
            break

        narration_lines.append(line)

    narration = " ".join(narration_lines)

    narration = re.sub(
        r"\s+",
        " ",
        narration
    ).strip()

    narration = re.sub(
        r"\*\*|__|`",
        "",
        narration
    )

    narration = re.sub(
        r"^(?:\d+[.)]\s*)+",
        "",
        narration
    )

    if len(narration) < 80:
        raise RuntimeError(
            "Narration was found, but it contains fewer "
            "than 80 characters. Check shorts_scripts.txt."
        )

    return narration


# ==========================================
# CAPTION SPLITTING
# ==========================================

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


# ==========================================
# CAPTION TIMING
# ==========================================

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
# TEXT WRAPPING
# ==========================================

def wrap_text(draw, text, selected_font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()

        bounds = draw.textbbox(
            (0, 0),
            test,
            font=selected_font
        )

        width = bounds[2] - bounds[0]

        if width > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test

    if current:
        lines.append(current)

    return lines


# ==========================================
# VIDEO FRAME DESIGN
# ==========================================

def make_frame(caption, number, total, path):
    # Create a smooth vertical gradient.
    image = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(image)

    top_color = (8, 13, 31)
    bottom_color = (18, 26, 62)

    for y in range(H):
        t = y / H

        color = tuple(
            int(
                top_color[channel]
                + (bottom_color[channel] - top_color[channel]) * t
            )
            for channel in range(3)
        )

        draw.line(
            (0, y, W, y),
            fill=color
        )

    # Background grid.
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

    # Brand header.
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

    # Section heading.
    draw.text(
        (82, 300),
        "THE INTERNET IS TALKING",
        font=font(30),
        fill=(105, 205, 235)
    )

    # Main caption card.
    draw.rounded_rectangle(
        (58, 560, 1022, 1350),
        radius=48,
        fill=(17, 27, 51),
        outline=(63, 91, 135),
        width=4
    )

    selected_font = font(76)

    lines = wrap_text(
        draw,
        caption,
        selected_font,
        830
    )

    # Reduce font size if needed.
    if len(lines) > 4:
        selected_font = font(60)

        lines = wrap_text(
            draw,
            caption,
            selected_font,
            850
        )

    line_height = 112
    total_height = len(lines) * line_height
    y = 560 + (790 - total_height) // 2

    for line in lines:
        bounds = draw.textbbox(
            (0, 0),
            line,
            font=selected_font
        )

        text_width = bounds[2] - bounds[0]
        x = (W - text_width) // 2

        draw.text(
            (x, y),
            line,
            font=selected_font,
            fill="white",
            stroke_width=1,
            stroke_fill=(5, 10, 24)
        )

        y += line_height

    # Footer.
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

    # Progress bar.
    left, right = 82, 998
    top, bottom = 1800, 1818

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

    image.save(
        path,
        optimize=True
    )


# ==========================================
# AI VOICE GENERATION
# ==========================================

async def create_voice(text, audio_path):
    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate="-5%"
    )

    await communicate.save(
        str(audio_path)
    )


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

    duration = float(
        result.stdout.strip()
    )

    return duration


# ==========================================
# CHECK REQUIRED PROGRAMS
# ==========================================

def check_requirements():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg is not installed or is not available."
        )

    if shutil.which("ffprobe") is None:
        raise RuntimeError(
            "FFprobe is not installed or is not available."
        )


# ==========================================
# CREATE VIDEO
# ==========================================

def main():
    print("================================")
    print("     TRENDCLIP DAILY")
    print("     VIDEO GENERATOR")
    print("================================")

    OUT.mkdir(
        parents=True,
        exist_ok=True
    )

    check_requirements()

    # Find narration.
    print("Reading narration...")

    narration = get_narration()

    print("Narration found successfully.")
    print("Narration characters:", len(narration))

    # Generate voiceover.
    print("Creating English AI voiceover...")

    audio = OUT / "voiceover.mp3"

    asyncio.run(
        create_voice(
            narration,
            audio
        )
    )

    if not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError(
            "Voiceover audio was not created."
        )

    print("Voiceover saved successfully.")

    # Measure audio.
    audio_duration = get_audio_duration(
        audio
    )

    if audio_duration <= 0:
        raise RuntimeError(
            "Audio duration could not be measured."
        )

    print(
        f"Voiceover duration: {audio_duration:.2f} seconds"
    )

    # Create caption groups.
    groups = split_captions(
        narration
    )

    if not groups:
        raise RuntimeError(
            "No caption groups were created."
        )

    weights = [
        syllable_weight(group)
        for group in groups
    ]

    total_weight = sum(weights)

    # Create frames.
    frames = OUT / "video_frames"

    frames.mkdir(
        parents=True,
        exist_ok=True
    )

    # Remove old frames to avoid stale files.
    for old_frame in frames.glob("frame_*.png"):
        old_frame.unlink()

    paths = []

    print(
        f"Creating {len(groups)} caption frames..."
    )

    for index, caption in enumerate(groups):
        frame_path = frames / f"frame_{index:03}.png"

        make_frame(
            caption,
            index,
            len(groups),
            frame_path
        )

        paths.append(
            frame_path
        )

    if not paths:
        raise RuntimeError(
            "No video frames were created."
        )

    # Create FFmpeg concat file.
    concat = OUT / "frames.txt"

    with concat.open(
        "w",
        encoding="utf-8"
    ) as file:

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

        # Repeat final frame for concat timing.
        file.write(
            f"file '{paths[-1].resolve()}'\n"
        )

    # Render final video.
    video = OUT / VIDEO_NAME

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
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(audio_duration),
            "-shortest",
            "-movflags", "+faststart",
            str(video)
        ],
        check=True
    )

    # Verify video.
    if not video.exists() or video.stat().st_size == 0:
        raise RuntimeError(
            "The final video was not created."
        )

    print("")
    print("================================")
    print("SUCCESS!")
    print("TRENDCLIP DAILY VIDEO CREATED!")
    print("================================")
    print("Video:", video)
    print(
        "File size:",
        round(video.stat().st_size / (1024 * 1024), 2),
        "MB"
    )


# ==========================================
# RUN PROGRAM
# ==========================================

if __name__ == "__main__":
    main()
