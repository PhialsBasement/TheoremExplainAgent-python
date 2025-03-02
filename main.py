import os
import sys
import logging
import argparse
import json
from pathlib import Path

from config import ANTHROPIC_API_KEY, MODEL_NAME
from agents.planner_agent import PlannerAgent
from agents.coding_agent import CodingAgent
from manim_handler.executor import ManimExecutor
from tts.tts_handler import TTSHandler
from utils.video_assembler import VideoAssembler
from utils.logger import setup_logging

def main(theorem_name, theorem_description, output_dir="outputs"):
    """Main execution function for TheoremExplainAgent."""
    try:
        # Create output directory first - before logging setup
        os.makedirs(output_dir, exist_ok=True)

        # Now set up logging after directory exists
        logger = setup_logging(log_file=os.path.join(output_dir, "theorem_explain_agent.log"))

        # Create sub-directories
        code_dir = os.path.join(output_dir, "code")
        media_dir = os.path.join(output_dir, "media")
        audio_dir = os.path.join(output_dir, "audio")
        final_dir = os.path.join(output_dir, "final")
        debug_dir = os.path.join(output_dir, "debug")

        for directory in [code_dir, media_dir, audio_dir, final_dir, debug_dir]:
            os.makedirs(directory, exist_ok=True)

        # Initialize components
        planner_agent = PlannerAgent()
        coding_agent = CodingAgent()
        manim_executor = ManimExecutor(output_dir=media_dir)
        tts_handler = TTSHandler(output_dir=audio_dir)
        video_assembler = VideoAssembler(output_dir=final_dir)

        # Step 1: Generate the video plan
        logger.info(f"Step 1: Generating video plan for {theorem_name}")
        scene_plan = planner_agent.generate_plan(theorem_name, theorem_description)

        if not scene_plan:
            logger.error("Failed to generate scene plan")
            return {"success": False, "error": "Failed to generate scene plan"}

        # Save the scene plan
        plan_file = os.path.join(output_dir, "scene_plan.json")
        with open(plan_file, "w") as f:
            json.dump(scene_plan, f, indent=2)

        logger.info(f"Scene plan saved to {plan_file}")

        # Step 2: Generate Manim code
        logger.info(f"Step 2: Generating Manim code")
        manim_code = coding_agent.generate_code(
            theorem_name,
            theorem_description,
            scene_plan,
            manim_executor,
            output_dir=output_dir
        )

        if not manim_code:
            logger.error("Failed to generate Manim code")
            return {"success": False, "error": "Failed to generate Manim code"}

        # Save the Manim code
        code_file = os.path.join(code_dir, "manim_code.py")
        with open(code_file, "w") as f:
            f.write(manim_code)

        logger.info(f"Manim code saved to {code_file}")

        # Step 3: Execute Manim code
        logger.info(f"Step 3: Executing Manim code")

        max_attempts = 5
        attempt = 0
        success = False
        error_message = ""
        output_files = []

        while attempt < max_attempts and not success:
            success, error_message, output_files = manim_executor.execute_code(
                manim_code,
                filename=code_file
            )

            if not success:
                logger.warning(f"Manim execution failed (attempt {attempt+1}/{max_attempts}): {error_message}")

                # Save the error message for debugging
                error_file = os.path.join(debug_dir, f"manim_error_{attempt+1}.txt")
                with open(error_file, "w") as f:
                    f.write(error_message)

                # Try to fix the code
                logger.info("Attempting to fix the code")
                fixed_code = coding_agent.fix_code(
                    theorem_name,
                    scene_plan[0] if scene_plan else {},  # Pass the first scene for simplicity
                    manim_code,
                    error_message,
                    output_dir=output_dir
                )

                if fixed_code:
                    # Update the code
                    manim_code = fixed_code

                    # Save the fixed code
                    fixed_code_file = os.path.join(code_dir, f"manim_code_fixed_{attempt+1}.py")
                    with open(fixed_code_file, "w") as f:
                        f.write(fixed_code)

                    logger.info(f"Fixed code saved to {fixed_code_file}")

                    # Use the fixed code file for the next attempt
                    code_file = fixed_code_file
                else:
                    logger.error("Failed to fix the code")
                    break

            attempt += 1

        if not success:
            logger.error(f"Failed to execute Manim code after {max_attempts} attempts")
            return {
                "success": False,
                "error": f"Failed to execute Manim code: {error_message}"
            }

        logger.info(f"Successfully generated {len(output_files)} video files")

        # Step 4: Generate audio narration
        logger.info(f"Step 4: Generating audio narration")
        audio_files = tts_handler.generate_scene_audio(scene_plan)

        # Step 5: Assemble the final video
        logger.info(f"Step 5: Assembling final video")
        final_video = video_assembler.assemble_video(
            output_files,
            audio_files,
            output_filename=os.path.join(final_dir, f"{theorem_name.replace(' ', '_')}_explanation.mp4")
        )

        if not final_video:
            logger.error("Failed to assemble final video")
            return {"success": False, "error": "Failed to assemble final video"}

        logger.info(f"Final video created: {final_video}")

        return {
            "success": True,
            "scene_plan": plan_file,
            "code_file": code_file,
            "output_files": output_files,
            "audio_files": list(audio_files.values()) if audio_files else [],
            "final_video": final_video
        }

    except Exception as e:
        # Create a basic logger if the main logger isn't set up yet
        if 'logger' not in locals():
            logging.basicConfig(level=logging.ERROR)
            logger = logging.getLogger(__name__)

        logger.error(f"Error in main execution: {str(e)}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TheoremExplainAgent")
    parser.add_argument("theorem_name", help="Name of the theorem")
    parser.add_argument("theorem_description", help="Description of the theorem")
    parser.add_argument("--output-dir", default="outputs", help="Output directory")

    args = parser.parse_args()

    result = main(args.theorem_name, args.theorem_description, args.output_dir)

    if result["success"]:
        print(f"Successfully created explanation video: {result['final_video']}")
    else:
        print(f"Failed to create explanation video: {result['error']}")
