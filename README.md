# TheoremExplainAgent

An implementation of the paper "TheoremExplainAgent: Towards Multimodal Explanations for LLM Theorem Understanding" using Anthropic's Claude 3.7 Sonnet model.

## Overview

TheoremExplainAgent is a system that generates multimodal theorem explanations in the form of educational videos. The system consists of two main agents:

1. **Planner Agent**: Creates detailed scene plans for explaining theorems
2. **Coding Agent**: Generates Manim animation code based on the scene plans

## Installation

### Prerequisites

- Python 3.8+
- Manim (for animations)
- FFmpeg (for video processing)
- LaTeX (for mathematical notation rendering)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/TheoremExplainAgent.git
   cd TheoremExplainAgent
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Manim dependencies (for Ubuntu/Debian):
   ```bash
   apt-get install libcairo2-dev libpango1.0-dev ffmpeg texlive-full
   ```

   For macOS (with Homebrew):
   ```bash
   brew install cairo pango ffmpeg
   brew install --cask mactex
   ```

4. Create a `.env` file with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

## Usage

### Basic usage:

```bash
python main.py "Pythagorean Theorem" "In a right-angled triangle, the square of the length of the hypotenuse is equal to the sum of the squares of the lengths of the other two sides."
```

### Using the example script:

```bash
cd examples
./run_example.py "Pythagorean Theorem"
```

Or to run all examples:

```bash
./run_example.py all
```

## Project Structure

- **agents/**: Contains the planner and coding agents
  - **prompts/**: Prompt templates for the agents
- **manim_handler/**: Handles Manim code execution and error fixing
- **tts/**: Text-to-speech generation
- **utils/**: Utility functions for video assembly, logging, etc.
- **examples/**: Example theorems and scripts

## How It Works

1. The planner agent creates a detailed scene plan for the theorem explanation
2. The coding agent generates Manim code based on the scene plan
3. The Manim executor runs the code and generates animation videos
4. The TTS handler generates audio narration for each scene
5. The video assembler combines the animations and narration into a final video

## License

MIT
