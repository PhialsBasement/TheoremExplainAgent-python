import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

# Model Configuration
MODEL_NAME = "claude-3-7-sonnet-20250219"

# Manim Configuration
MANIM_QUALITY = "medium_quality"  # Options: low_quality, medium_quality, high_quality
MANIM_OUTPUT_DIR = "media"

# TTS Configuration
TTS_ENGINE = "gTTS"  # Options: gTTS, etc.

# Logging Configuration
LOG_LEVEL = "INFO"
