
import asyncio
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# TRENDCLIP AI - ENHANCED YOUTUBE SHORTS
# ==========================================

OUT = Path("output")
FRAMES = OUT / "video_frames"

W, H = 1080, 1920
FPS = 30

VOICE = "en-US-AriaNeural"
VOICE_RATE = "+8%"
VIDEO_NAME = "trendclip_first_short.mp4"

# Two words per caption keeps the video moving.
CAPTION_WORDS = 2

WHITE = (255, 255, 255)
YELLOW = (255, 220, 35)
CYAN = (50, 220, 255)
DARK = (5, 8, 20)

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]

# ==========================================
# FONT HELPERS
# ==========================================

def font(size):
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


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

    while size > 38:
        selected = font(size)

        if text_width(draw, text, selected) <= maximum_width:
            return selected

        size -= 4

    return font(38)


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
            "Could not find shorts_scripts.txt"
        )

    script = script_path.read_text(
        encoding="utf-8"
    ).strip()

    if not script:
        raise RuntimeError("The script file is empty.")

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

    for index, line in enumerate(lines):
        match = start_pattern.match(line)

        if match:
            start_index = index
            first_line = match.group(1).strip()
            break

    if start_index is None:
        raise RuntimeError(
            "Could not find a Narration or Voiceover heading."
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

    for index in range(0, len(words), max_words):
        groups.append(words[index:index + max_words])

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
    draw = ImageDraw.Draw(image)

    top_color = (4, 8, 24)
    bottom_color = (20, 15, 58)

    # Smooth vertical gradient.
    for y in range(H):
        t = y / H

        color = tuple(
            int(
                top_color[channel] * (1 - t)
                + bottom_color[channel] * t
            )
            for channel in range(3)
        )

        draw.line(
            (0, y, W, y),
            fill=color
        )

    # Moving decorative rings.
    for i in range(8):
        x = (i * 193 + number * 83) % W
        y = (i * 271 + number * 47) % H
        radius = 90 + (i % 4) * 35

        draw.ellipse(
            (
                x - radius,
                y - radius,
                x + radius,
                y + radius
            ),
            outline=(22, 43, 91),
            width=4
        )

    # Diagonal background streaks.
    offset = (number * 35) % 180

    for x in range(-H, W, 180):
        draw.line(
            (
                x + offset,
                0,
                x + H + offset,
                H
            ),
            fill=(15, 28, 58),
            width=3
        )

    # Accent glow panel.
    draw.ellipse(
        (250, 480, 830, 1060),
        outline=(18, 42, 90),
        width=8
    )

    return image


# ==========================================
# TEXT DRAWING
# ==========================================

def draw_centered_text(
    draw,
    text,
    y,
    selected_font,
    fill,
    stroke_width=0,
    stroke_fill=(0, 0, 0)
):
    box = draw.textbbox(
        (0, 0),
        text,
        font=selected_font,
        stroke_width=stroke_width
    )

    width = box[2] - box[0]
    x = (W - width) // 2

    draw.text(
        (x, y),
        text,
        font=selected_font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill
    )

    return x, width


# ==========================================
# SHORTS FRAME DESIGN
# ==========================================

def make_frame(words, number, total, path):
    image = create_background(number)
    draw = ImageDraw.Draw(image)

    # Main top branding.
    draw.rounded_rectangle(
        (55, 85, 1025, 215),
        radius=38,
        fill=(13, 23, 49),
        outline=(48, 83, 143),
        width=4
    )

    draw.text(
        (95, 119),
        "TRENDCLIP",
        font=font(45),
        fill=WHITE
    )

    draw.text(
        (425, 128),
        "AI",
        font=font(38),
        fill=YELLOW
    )

    # Trending indicator.
    draw.rounded_rectangle(
        (755, 120, 980, 180),
        radius=22,
        fill=(135, 25, 42)
    )

    draw.ellipse(
        (775, 140, 795, 160),
        fill=(255, 70, 75)
    )

    draw.text(
        (810, 130),
        "TRENDING",
        font=font(25),
        fill=WHITE
    )

    # Attention-grabbing hook label.
    hook_text = (
        "WAIT FOR IT"
        if number == 0
        else "YOU NEED TO SEE THIS"
    )

    hook_font = fit_font(
        draw,
        hook_text,
        36,
        850
    )

    draw_centered_text(
        draw,
        hook_text,
        355,
        hook_font,
        CYAN
    )

    # Main caption panel.
    draw.rounded_rectangle(
        (55, 570, 1025, 1325),
        radius=55,
        fill=(9, 16, 37),
        outline=(45, 75, 132),
        width=5
    )

    # Small caption heading.
    draw_centered_text(
        draw,
        "THE STORY CONTINUES...",
        660,
        font(27),
        (150, 190, 230)
    )

    # Main caption: highlight the final word.
    caption_words = [word.upper() for word in words]

    if not caption_words:
        caption_words = ["KEEP", "WATCHING"]

    first_part = " ".join(caption_words[:-1])
    highlighted_word = caption_words[-1]

    first_font = fit_font(
        draw,
        first_part,
        104,
        850
    )

    highlight_font = fit_font(
        draw,
        highlighted_word,
        112,
        850
    )

    first_width = (
        text_width(draw, first_part, first_font)
        if first_part else 0
    )

    highlight_width = text_width(
        draw,
        highlighted_word,
        highlight_font
    )

    gap = 18 if first_part else 0
    total_width = first_width + gap + highlight_width
    start_x = (W - total_width) // 2

    # First caption word(s).
    if first_part:
        draw.text(
            (start_x + 5, 895 + 8),
            first_part,
            font=first_font,
            fill=(0, 0, 0),
            stroke_width=5,
            stroke_fill=(0, 0, 0)
        )

        draw.text(
            (start_x, 895),
            first_part,
            font=first_font,
            fill=WHITE,
            stroke_width=3,
            stroke_fill=(0, 0, 0)
        )

    # Highlight background.
    highlight_x = start_x + first_width + gap

    draw.rounded_rectangle(
        (
            highlight_x - 18,
            1050,
            highlight_x + highlight_width + 18,
            1185
        ),
        radius=22,
        fill=(58, 47, 9),
        outline=(125, 100, 20),
        width=3
    )

    # Highlighted word.
    draw.text(
        (highlight_x, 1060),
        highlighted_word,
        font=highlight_font,
        fill=YELLOW,
        stroke_width=3,
        stroke_fill=(0, 0, 0)
    )

    # Bottom callout.
    draw_centered_text(
        draw,
        "DON'T SCROLL!",
        1450,
        font(52),
        YELLOW
    )

    draw_centered_text(
        draw,
        "MORE STORIES. MORE TRENDS.",
        1535,
        font(29),
        WHITE
    )

    # Stronger closing message on final scene.
    if number == total - 1:
        draw.rounded_rectangle(
            (180, 1610, 900, 1700),
            radius=28,
            fill=(18, 48, 78),
            outline=CYAN,
            width=3
        )

        draw_centered_text(
            draw,
            "FOLLOW FOR MORE!",
            1628,
            font(35),
            CYAN
        )

    # Video progress bar.
    left = 75
    right = 1005
    bar_top = 1790
    bar_bottom = 1816

    draw.rounded_rectangle(
        (left, bar_top, right, bar_bottom),
        radius=13,
        fill=(45, 53, 77)
    )

    progress = int(
        (number + 1) / max(total, 1) * (right - left)
    )

    draw.rounded_rectangle(
        (
            left,
            bar_top,
            left + progress,
            bar_bottom
        ),
        radius=13,
        fill=YELLOW
    )

    # Scene counter.
    draw.text(
        (850, 1725),
        f"{number + 1}/{total}",
        font=font(25),
        fill=(170, 195, 225)
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
    video_filter = (
        "fps=30,"
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.00045,1.055)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=1:"
        "s=1080x1920:"
        "fps=30,"
        "setsar=1,"
        "format=yuv420p"
    )

    command = [
        "ffmpeg",
        "-y",

        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),

        "-i", str(audio),

        "-map", "0:v:0",
        "-map", "1:a:0",

        "-vf", video_filter,

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
    print("       ENHANCED VIDEO GENERATOR")
    print("======================================")

    OUT.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)

    check_requirements()

    # Step 1: Read narration.
    print("\n[1/6] Reading narration...")

    narration = get_narration()

    print("Narration loaded.")
    print("Characters:", len(narration))

    # Step 2: Create voiceover.
    print("\n[2/6] Creating AI voiceover...")

    audio = OUT / "voiceover.mp3"

    asyncio.run(
        create_voice(narration, audio)
    )

    if not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError(
            "Voiceover generation failed."
        )

    duration = get_audio_duration(audio)

    if duration <= 0:
        raise RuntimeError(
            "Invalid audio duration."
        )

    print(f"Audio duration: {duration:.2f} seconds")

    # Step 3: Create captions.
    print("\n[3/6] Creating fast captions...")

    groups = split_captions(narration)

    if not groups:
        raise RuntimeError(
            "No captions were created."
        )

    weights = [
        syllable_weight(" ".join(group))
        for group in groups
    ]

    total_weight = sum(weights)

    # Step 4: Create visual frames.
    print("\n[4/6] Designing Shorts visuals...")

    for old_frame in FRAMES.glob("frame_*.png"):
        old_frame.unlink()

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
        raise RuntimeError(
            "No video frames were generated."
        )

    # Step 5: Build video timeline.
    print("\n[5/6] Preparing video timeline...")

    concat_file = OUT / "frames.txt"

    with concat_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        for index, frame_path in enumerate(paths):
            segment_duration = (
                duration * weights[index] / total_weight
            )

            file.write(
                f"file '{frame_path.resolve()}'\n"
            )

            file.write(
                f"duration {segment_duration:.5f}\n"
            )

        file.write(
            f"file '{paths[-1].resolve()}'\n"
        )

    # Step 6: Render final video.
    print("\n[6/6] Rendering YouTube Short...")

    video = OUT / VIDEO_NAME

    render_video(
        concat_file,
        audio,
        video,
        duration
    )

    if not video.exists() or video.stat().st_size == 0:
        raise RuntimeError(
            "The final video was not created."
        )

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
