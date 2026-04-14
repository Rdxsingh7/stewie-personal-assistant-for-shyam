"""
Stewie Screen Reader — Screenshot capture, OCR, and summarization.

Two-tier approach:
- Tier 1: Screenshot + Tesseract OCR (universal)
- Tier 2: LLM-powered summarization of extracted text
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

import mss
import pytesseract
from loguru import logger
from PIL import Image

# ═══════════════════════════════════════════
# TESSERACT CONFIGURATION
# ═══════════════════════════════════════════

# Common Windows install paths for Tesseract
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Users\{username}\AppData\Local\Tesseract-OCR\tesseract.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tesseract-OCR", "tesseract.exe"),
]

def _setup_tesseract():
    """Locate and configure Tesseract executable."""
    # Check if already on PATH
    try:
        import subprocess
        subprocess.run(["tesseract", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try common paths
    for path_template in TESSERACT_PATHS:
        try:
            # Resolve {username} if present
            path = path_template.format(username=os.getlogin())
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.debug(f"Tesseract located at: {path}")
                return True
        except Exception:
            continue
    
    return False

# Attempt initial setup
_HAS_TESSERACT = _setup_tesseract()


# ═══════════════════════════════════════════
# SCREEN CAPTURE
# ═══════════════════════════════════════════


def capture_screen() -> Image.Image:
    """
    Capture the primary monitor as a PIL Image.

    Returns:
        PIL Image of the current screen.
    """
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        screenshot = sct.grab(monitor)
        # Convert BGRA → RGB
        img = Image.frombytes(
            "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
        )
        return img


def capture_screen_to_file(
    save_dir: Optional[str] = None,
) -> str:
    """
    Capture the screen and save to a temporary file.

    Args:
        save_dir: Directory to save the screenshot. Defaults to temp dir.

    Returns:
        Path to the saved screenshot file.
    """
    img = capture_screen()

    if save_dir:
        save_path = Path(save_dir) / "stewie_screenshot.png"
    else:
        save_path = Path(tempfile.mktemp(suffix=".png", prefix="stewie_"))

    img.save(str(save_path))
    logger.info(f"Screenshot saved to: {save_path}")
    return str(save_path)


# ═══════════════════════════════════════════
# OCR — TEXT EXTRACTION
# ═══════════════════════════════════════════


def _ocr_image(image: Image.Image) -> str:
    """
    Extract text from an image using Tesseract OCR.

    Args:
        image: PIL Image to OCR.

    Returns:
        Extracted text.
    """
    if not _HAS_TESSERACT and not _setup_tesseract():
        raise RuntimeError(
            "Tesseract OCR is not installed or not in your PATH. "
            "Please ensure Tesseract is installed at C:\\Program Files\\Tesseract-OCR"
        )

    try:
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise


# ═══════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════


async def read_screen() -> str:
    """
    Capture the screen and extract text via OCR.

    Returns:
        Extracted text from the current screen.
    """
    logger.info("Reading screen content via OCR...")
    image = capture_screen()
    text = _ocr_image(image)

    if text:
        word_count = len(text.split())
        logger.info(f"Screen read complete: {word_count} words extracted")
    else:
        logger.warning("No text could be extracted from the screen")
        text = "No readable text was found on the screen."

    return text


async def summarize_screen(
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> str:
    """
    Capture the screen, OCR it, and produce a smart summary.

    Uses the LLM to summarize the extracted screen content
    in a JARVIS-style, helpful manner.

    Args:
        api_key: OpenAI API key (if not using global config).
        model: OpenAI model to use for summarization.

    Returns:
        A concise summary of what's on screen.
    """
    # Get the raw screen text
    raw_text = await read_screen()

    if "No readable text" in raw_text:
        return raw_text

    # Truncate to avoid token limits
    max_chars = 4000
    truncated = raw_text[:max_chars]
    if len(raw_text) > max_chars:
        truncated += "\n... [truncated]"

    # Summarize with LLM
    try:
        from openai import AsyncOpenAI

        # Load API key from environment if not provided
        if not api_key:
            from config.settings import load_config

            config = load_config()
            api_key = config.openai_api_key

        client = AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Stewie, a sophisticated AI assistant. "
                        "Summarize the following screen content concisely "
                        "and helpfully. Be clear and structured. "
                        "Address the user as 'sir'."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Summarize this screen content:\n\n{truncated}",
                },
            ],
            max_tokens=500,
            temperature=0.3,
        )

        summary = response.choices[0].message.content
        logger.info("Screen summarized successfully")
        return summary

    except Exception as e:
        logger.error(f"Screen summarization failed: {e}")
        # Return raw text as fallback
        return f"I couldn't generate a summary, but here's the raw content:\n\n{truncated}"
