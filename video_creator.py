
import asyncio
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# TRENDCLIP AI - VERSION 4
# WORD-LEVEL CAPTIONS + DYNAMIC VISUALS
# ==========================================

OUT = Path("output")
FRAMES = OUT / "video_frames"

W, H = 1080, 1920
FPS = 30

VOICE = "en-US-AriaNeural"
VOICE_RATE = "+8%"

VIDEO_NAME = "trendclip_first_short.mp4"

CTA_DURATION = 1.4
WORDS_PER_SCENE = 4

WHITE = (255, 255, 255)
YELLOW = (255, 220, 35)
CYAN = (50, 220, 255)

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]

PALETTES = [
    ((4, 8, 28), (20, 18, 70), (30, 100, 210)),
    ((20, 5, 35), (65, 12, 75), (200, 40, 140)),
    ((3, 20, 30), (5, 55, 75), (20, 190, 190)),
    ((25, 8, 5), (85, 25, 12), (235, 110, 25)),
    ((5, 12, 25), (15, 35, 75), (80, 120, 255)),
]


# ==========================================
# FONTS
# ==========================================

def font(size):
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def text_width(draw, text, selected_font):
    box = draw.textbbox((0, 0), text, font=selected_font)
    return box[2] - box[0]


def fit_font(draw, text, starting_size, maximum_width):
    size = starting_size

    while size > 38:
        selected = font(size)

        if text_width(draw, text, selected) <= maximum_width:
            return selected

        size -= 4

    return font(38)


def centered_text(draw, text, y, selected_font, fill):
    width = text_width(draw, text, selected_font)

    draw.text(
        ((W - width) // 2, y),
        text,
        font=selected_font,
        fill=fill,
        stroke_width=3,
        stroke_fill=(0, 0, 0),
    )


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
        None,
    )

    if script_path is None:
        raise FileNotFoundError("shorts_scripts.txt was not found.")

    script = script_path.read_text(encoding="utf-8").strip()

    if not script:
        raise RuntimeError("The script file is empty.")

    start_pattern = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?:\*\*)?"
        r"(?:\d+[.)]\s*)?"
        r"(?:original\s+)?"
        r"(?:narration|voice[- ]?over|voiceover|spoken script)"
        r"(?:\*\*)?\s*[:\-–—]?\s*(.*)$",
        re.I,
    )

    stop_pattern = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?:\*\*)?"
        r"(?:title|caption|description|hashtags|tags|"
        r"three suggested visual scenes|suggested visual scenes|"
        r"visual scenes|short on-screen captions|"
        r"on-screen captions|suggested visuals|"
        r"visual suggestions|fact-check)"
        r"(?:\*\*)?\s*[:\-–—]?\s*$",
        re.I,
    )

    lines = script.splitlines()
    narration_lines = []
    start_index = None
    first_line = ""

    for index, line in enumerate(lines):
        match = start_pattern.match(line)

        if match:
            start_index = index
            first_line = match.group(1).strip()
            break

    if start_index is not None:
        if first_line:
            narration_lines.append(first_line)

        for line in lines[start_index + 1:]:
            if stop_pattern.match(line):
                break

            narration_lines.append(line)
    else:
        narration_lines = lines

    narration = " ".join(narration_lines)
    narration = re.sub(r"\*\*|__|`|~~", "", narration)
    narration = re.sub(r"^\s*[-*•]\s+", "", narration, flags=re.M)
    narration = re.sub(r"\s+", " ", narration).strip()

    if len(narration) < 80:
        raise RuntimeError(
            "Narration is too short. Check shorts_scripts.txt."
        )

    return narration


# ==========================================
# WORD TIMING
# ==========================================

async def create_voice(text, audio_path):
    """
    Generate audio and collect Edge TTS word-boundary events.
    Offsets are supplied in 100-nanosecond units.
    """

    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate=VOICE_RATE,
    )

    audio_chunks = []
    boundaries = []

    try:
        async for item in communicate.stream():
            if item["type"] == "audio":
                audio_chunks.append(item["data"])

            elif item["type"] == "WordBoundary":
                boundaries.append({
                    "text": item["text"],
                    "start": item["offset"] / 10_000_000,
                })

        if not audio_chunks:
            raise RuntimeError("No audio data received from Edge TTS.")

        audio_path.write_bytes(b"".join(audio_chunks))

    except Exception as error:
        print("Word timing unavailable:", error)
        print("Trying standard voice generation...")

        if audio_path.exists():
            audio_path.unlink()

        fallback = edge_tts.Communicate(
            text,
            VOICE,
            rate=VOICE_RATE,
        )

        await fallback.save(str(audio_path))
        boundaries = []

    return boundaries


def get_audio_duration(audio_path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return float(result.stdout.strip())


def make_timeline(narration, boundaries, duration):
    """
    Use real word-boundary timestamps when available.
    Otherwise, estimate timing based on word length.
    """

    if boundaries:
        boundaries.sort(key=lambda item: item["start"])

        valid = [
            item for item in boundaries
            if item["text"].strip()
            and 0 <= item["start"] < duration
        ]

        timeline = []

        for index, item in enumerate(valid):
            start = item["start"]

            if index + 1 < len(valid):
                end = valid[index + 1]["start"]
            else:
                end = duration

            if end <= start:
                continue

            timeline.append({
                "word": item["text"].strip(),
                "start": start,
                "end": end,
            })

        if timeline:
            if timeline[0]["start"] > 0:
                timeline[0]["start"] = 0

            return timeline

    print("Using estimated word timing as fallback.")

    words = narration.split()

    weights = [
        max(1, len(re.findall(r"[aeiouy]+", word.lower())))
        for word in words
    ]

    total_weight = sum(weights) or 1
    current = 0.0
    timeline = []

    for word, weight in zip(words, weights):
        segment = duration * weight / total_weight

        timeline.append({
            "word": word,
            "start": current,
            "end": current + segment,
        })

        current += segment

    if timeline:
        timeline[-1]["end"] = duration

    return timeline


# ==========================================
# DYNAMIC BACKGROUNDS
# ==========================================

def create_background(scene_number):
    top, bottom, accent = PALETTES[
        scene_number % len(PALETTES)
    ]

    # Create a small vertical gradient and enlarge it.
    gradient = Image.new("RGB", (1, H))
    draw_gradient = ImageDraw.Draw(gradient)

    for y in range(H):
        t = y / max(H - 1, 1)

        color = tuple(
            int(top[c] * (1 - t) + bottom[c] * t)
            for c in range(3)
        )

        draw_gradient.line((0, y, 1, y), fill=color)

    image = gradient.resize((W, H))
    draw = ImageDraw.Draw(image)

    shift = (scene_number * 137) % 500

    # Large glowing-style rings.
    for i in range(5):
        x = (170 + i * 230 + shift) % (W + 250) - 100
        y = 350 + i * 280
        radius = 110 + (i % 3) * 60

        draw.ellipse(
            (
                x - radius,
                y - radius,
                x + radius,
                y + radius,
            ),
            outline=accent,
            width=5,
        )

    # Diagonal light streaks.
    for x in range(-H, W, 240):
        draw.line(
            (
                x + shift,
                0,
                x + H + shift,
                H,
            ),
            fill=tuple(int(c * 0.45) for c in accent),
            width=4,
        )

    # Central spotlight.
    draw.ellipse(
        (160, 530, 920, 1290),
        outline=tuple(int(c * 0.75) for c in accent),
        width=8,
    )

    return image


# ==========================================
# SHORTS FRAME DESIGN
# ==========================================

def make_word_frame(
    word,
    previous_word,
    index,
    total,
    scene_number,
    background,
    path,
):
    image = background.copy()
    draw = ImageDraw.Draw(image)

    _, _, accent = PALETTES[
        scene_number % len(PALETTES)
    ]

    # Top brand bar.
    draw.rounded_rectangle(
        (55, 75, 1025, 205),
        radius=35,
        fill=(8, 13, 35),
        outline=accent,
        width=4,
    )

    draw.text(
        (95, 115),
        "TRENDCLIP AI",
        font=font(43),
        fill=WHITE,
    )

    draw.rounded_rectangle(
        (750, 112, 980, 175),
        radius=25,
        fill=(125, 22, 45),
    )

    draw.ellipse(
        (770, 132, 793, 155),
        fill=(255, 75, 75),
    )

    draw.text(
        (810, 125),
        "LIVE",
        font=font(28),
        fill=WHITE,
    )

    # Rotating hook labels.
    hooks = [
        "WAIT FOR IT",
        "HERE'S THE TWIST",
        "BREAKING IT DOWN",
        "WATCH THIS",
        "THE BIG QUESTION",
    ]

    hook = hooks[scene_number % len(hooks)]

    centered_text(
        draw,
        hook,
        340,
        font(39),
        CYAN,
    )

    # Caption panel.
    draw.rounded_rectangle(
        (55, 570, 1025, 1330),
        radius=55,
        fill=(7, 12, 30),
        outline=accent,
        width=6,
    )

    centered_text(
        draw,
        "LISTEN CLOSELY",
        660,
        font(30),
        (160, 190, 225),
    )

    # Previous word provides context.
    if previous_word:
        previous = previous_word.upper()

        previous_font = fit_font(
            draw,
            previous,
            55,
            850,
        )

        centered_text(
            draw,
            previous,
            850,
            previous_font,
            (135, 155, 190),
        )

    # Current word gets the strongest emphasis.
    display_word = word.upper()

    selected_font = fit_font(
        draw,
        display_word,
        145,
        880,
    )

    width = text_width(draw, display_word, selected_font)
    x = (W - width) // 2

    # Highlight background.
    draw.rounded_rectangle(
        (
            x - 35,
            1000,
            x + width + 35,
            1200,
        ),
        radius=35,
        fill=(58, 46, 8),
        outline=YELLOW,
        width=5,
    )

    draw.text(
        (x, 1025),
        display_word,
        font=selected_font,
        fill=YELLOW,
        stroke_width=5,
        stroke_fill=(0, 0, 0),
    )

    # Bottom callouts.
    centered_text(
        draw,
        "DON'T SCROLL!",
        1460,
        font(53),
        YELLOW,
    )

    centered_text(
        draw,
        "THE LATEST STORIES IN ONE PLACE",
        1540,
        font(27),
        WHITE,
    )

    # Progress bar.
    left = 75
    right = 1005
    top = 1785
    bottom = 1815

    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=15,
        fill=(45, 53, 77),
    )

    progress = int(
        (index + 1) / max(total, 1) * (right - left)
    )

    draw.rounded_rectangle(
        (left, top, left + progress, bottom),
        radius=15,
        fill=YELLOW,
    )

    draw.text(
        (820, 1705),
        f"{index + 1}/{total}",
        font=font(28),
        fill=WHITE,
    )

    image.save(path, optimize=True)


# ==========================================
# END CARD
# ==========================================

def make_end_card(path):
    image = create_background(99)
    draw = ImageDraw.Draw(image)

    centered_text(
        draw,
        "THANKS FOR WATCHING",
        650,
        font(62),
        WHITE,
    )

    centered_text(
        draw,
        "FOLLOW FOR MORE",
        850,
        font(75),
        YELLOW,
    )

    centered_text(
        draw,
        "TRENDCLIP AI",
        1050,
        font(55),
        CYAN,
    )

    draw.rounded_rectangle(
        (150, 1250, 930, 1390),
        radius=45,
        fill=(10, 35, 65),
        outline=CYAN,
        width=5,
    )

    centered_text(
        draw,
        "MORE TRENDS. MORE STORIES.",
        1290,
        font(32),
        WHITE,
    )

    image.save(path, optimize=True)


# ==========================================
# FFMPEG REQUIREMENTS
# ==========================================

def check_requirements():
    for program in ("ffmpeg", "ffprobe"):
        if shutil.which(program) is None:
            raise RuntimeError(
                f"{program} is not installed."
            )


# ==========================================
# CONCAT FILE
# ==========================================

def concat_path(path):
    return str(path.resolve()).replace("'", "'\\''")


def build_concat_file(timeline, paths, end_card, concat_file):
    with concat_file.open("w", encoding="utf-8") as file:
        for item, frame_path in zip(timeline, paths):
            segment_duration = max(
                0.06,
                item["end"] - item["start"],
            )

            file.write(
                f"file '{concat_path(frame_path)}'\n"
            )

            file.write(
                f"duration {segment_duration:.6f}\n"
            )

        file.write(
            f"file '{concat_path(end_card)}'\n"
        )

        file.write(
            f"duration {CTA_DURATION:.6f}\n"
        )

        # Repeat the last image for concat demuxer timing.
        file.write(
            f"file '{concat_path(end_card)}'\n"
        )


# ==========================================
# VIDEO RENDERING
# ==========================================

def render_video(concat_file, audio, video, duration):
    total_duration = duration + CTA_DURATION

    video_filter = (
        "fps=30,"
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.00035,1.06)':"
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
        "-af", f"apad=pad_dur={CTA_DURATION}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "160k",
        "-t", str(total_duration),
        "-movflags", "+faststart",
        str(video),
    ]

    subprocess.run(command, check=True)


# ==========================================
# MAIN GENERATOR
# ==========================================

def main():
    print("")
    print("========================================")
    print("       TRENDCLIP AI - VERSION 4")
    print("       DYNAMIC SHORTS GENERATOR")
    print("========================================")

    OUT.mkdir(parents=True, exist_ok=True)

    if FRAMES.exists():
        shutil.rmtree(FRAMES)

    FRAMES.mkdir(parents=True, exist_ok=True)

    check_requirements()

    # 1. Narration.
    print("\n[1/7] Reading narration...")

    narration = get_narration()

    print("Narration loaded:", len(narration), "characters")

    # 2. Voice and word timing.
    print("\n[2/7] Generating AI voice and word timing...")

    audio = OUT / "voiceover.mp3"

    boundaries = asyncio.run(
        create_voice(narration, audio)
    )

    if not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError("Voiceover generation failed.")

    duration = get_audio_duration(audio)

    if duration <= 0:
        raise RuntimeError("Invalid audio duration.")

    print("Audio duration:", round(duration, 2), "seconds")
    print("Word timing events:", len(boundaries))

    # 3. Timeline.
    print("\n[3/7] Building caption timeline...")

    timeline = make_timeline(
        narration,
        boundaries,
        duration,
    )

    if not timeline:
        raise RuntimeError("No caption timings were created.")

    print("Caption count:", len(timeline))

    # 4. Create changing backgrounds.
    print("\n[4/7] Creating dynamic visual scenes...")

    backgrounds = {}

    paths = []

    for index, item in enumerate(timeline):
        scene_number = index // WORDS_PER_SCENE

        if scene_number not in backgrounds:
            backgrounds[scene_number] = create_background(
                scene_number
            )

        previous_word = (
            timeline[index - 1]["word"]
            if index > 0
            else ""
        )

        frame_path = FRAMES / f"word_{index:04d}.png"

        make_word_frame(
            item["word"],
            previous_word,
            index,
            len(timeline),
            scene_number,
            backgrounds[scene_number],
            frame_path,
        )

        paths.append(frame_path)

        print(
            f"Created caption {index + 1}/{len(timeline)}"
        )

    # 5. End card.
    print("\n[5/7] Creating end card...")

    end_card = FRAMES / "end_card.png"
    make_end_card(end_card)

    # 6. Timeline file.
    print("\n[6/7] Preparing video timeline...")

    concat_file = OUT / "frames.txt"

    build_concat_file(
        timeline,
        paths,
        end_card,
        concat_file,
    )

    # 7. Render.
    print("\n[7/7] Rendering final YouTube Short...")

    video = OUT / VIDEO_NAME

    render_video(
        concat_file,
        audio,
        video,
        duration,
    )

    if not video.exists() or video.stat().st_size == 0:
        raise RuntimeError("The final video was not created.")

    size_mb = video.stat().st_size / (1024 * 1024)

    print("")
    print("========================================")
    print("          VIDEO COMPLETE!")
    print("========================================")
    print("File:", video)
    print("Audio duration:", round(duration, 2), "seconds")
    print("Total video duration:", round(duration + CTA_DURATION, 2))
    print("Word captions:", len(timeline))
    print("Resolution: 1080 x 1920")
    print("FPS:", FPS)
    print("File size:", round(size_mb, 2), "MB")
    print("========================================")


if __name__ == "__main__":
    main()
