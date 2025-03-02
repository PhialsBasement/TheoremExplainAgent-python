import logging
import re
import os
import json
from config import ANTHROPIC_API_KEY, MODEL_NAME
from utils.anthropic_client import AnthropicClient
from agents.prompts.coding_prompts import (
    get_coding_prompt,
    get_code_fixing_prompt,
    get_single_scene_coding_prompt,
    get_single_scene_fixing_prompt
)

logger = logging.getLogger(__name__)

class CodingAgent:
    def __init__(self):
        self.client = AnthropicClient(ANTHROPIC_API_KEY, MODEL_NAME)
        logger.info("Initialized CodingAgent")

    def generate_code(self, theorem_name, theorem_description, scene_plan, manim_executor=None, output_dir=None):
        """Generate Manim code for the given scene plan, testing each scene as it's generated."""
        logger.info(f"Generating Manim code for {theorem_name} with {len(scene_plan)} scenes")

        # Initialize containers for scene code
        scene_codes = {}
        failed_scenes = {}

        # Create a temp directory for scene testing
        temp_dir = None
        if output_dir:
            temp_dir = os.path.join(output_dir, "temp_scenes")
            os.makedirs(temp_dir, exist_ok=True)

        # Process each scene individually
        for i, scene in enumerate(scene_plan):
            scene_number = i + 1
            scene_title = scene.get('title', f'Scene{scene_number}')
            logger.info(f"Generating code for Scene {scene_number}: {scene_title}")

            # Generate code for this specific scene
            scene_code = self.generate_scene_code(
                theorem_name,
                theorem_description,
                scene,
                scene_number,
                output_dir
            )

            if not scene_code:
                logger.error(f"Failed to generate code for Scene {scene_number}")
                failed_scenes[scene_number] = {
                    'scene': scene,
                    'error': "Code generation failed"
                }
                continue

            # Create a complete standalone file with just this scene for testing
            class_name = self._generate_class_name(scene_title, scene_number)
            standalone_code = f"""from manim import *

# Constants for frame dimensions
config.frame_height = 8
config.frame_width = 14

{scene_code}

if __name__ == "__main__":
    pass
"""

            # Save to a temporary file
            if temp_dir:
                temp_file_path = os.path.join(temp_dir, f"scene_{scene_number}_test.py")
                with open(temp_file_path, "w") as f:
                    f.write(standalone_code)

                # Now test the scene using direct execution
                try:
                    import subprocess
                    logger.info(f"Validating Scene {scene_number} with direct execution")

                    # Use Python to validate syntax (fast check)
                    cmd = ["python", "-m", "py_compile", temp_file_path]
                    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    # If syntax check fails, report it
                    syntax_ok = True
                    if process.returncode != 0:
                        syntax_ok = False
                        error_message = process.stderr
                        logger.warning(f"Scene {scene_number} syntax validation failed: {error_message}")

                        # Try to fix the syntax
                        scene_code = self._attempt_to_fix_scene(
                            theorem_name, scene, scene_number, scene_code, error_message,
                            max_fix_attempts=3, output_dir=output_dir
                        )

                        if not scene_code:
                            logger.error(f"Failed to fix Scene {scene_number} syntax errors after multiple attempts")
                            failed_scenes[scene_number] = {
                                'scene': scene,
                                'error': error_message
                            }
                            continue

                        # Update the standalone code with the fixed version
                        standalone_code = f"""from manim import *

# Constants for frame dimensions
config.frame_height = 8
config.frame_width = 14

{scene_code}

if __name__ == "__main__":
    pass
"""
                        with open(temp_file_path, "w") as f:
                            f.write(standalone_code)

                    # If syntax is OK (or was fixed), try rendering
                    if syntax_ok or scene_code:
                        # Try to render with low quality and no preview to be fast
                        logger.info(f"Attempting to render Scene {scene_number} with Manim")
                        cmd = ["manim", temp_file_path, class_name, "-ql", "--disable_caching"]
                        logger.info(f"Executing: {' '.join(cmd)}")

                        # Max attempts for rendering
                        max_render_attempts = 5
                        for render_attempt in range(max_render_attempts):
                            try:
                                process = subprocess.run(
                                    cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    timeout=60  # Timeout after 60 seconds
                                )

                                if process.returncode == 0:
                                    # Success!
                                    logger.info(f"Scene {scene_number} rendered successfully on attempt {render_attempt+1}")
                                    break
                                else:
                                    error_message = f"{process.stdout}\n{process.stderr}"
                                    logger.warning(f"Scene {scene_number} rendering failed (attempt {render_attempt+1}/{max_render_attempts}): {error_message}")

                                    # Try to fix rendering issues
                                    fixed_code = self.fix_scene_code(
                                        theorem_name,
                                        scene,
                                        scene_number,
                                        scene_code,
                                        error_message,
                                        max_attempts=1,  # Single attempt per round
                                        output_dir=output_dir
                                    )

                                    if fixed_code:
                                        logger.info(f"Fixed Scene {scene_number} rendering issues on attempt {render_attempt+1}")
                                        scene_code = fixed_code

                                        # Update the test file
                                        with open(temp_file_path, "w") as f:
                                            f.write(f"""from manim import *

# Constants for frame dimensions
config.frame_height = 8
config.frame_width = 14

{scene_code}

if __name__ == "__main__":
    pass
""")
                                    else:
                                        logger.warning(f"Failed to fix Scene {scene_number} on attempt {render_attempt+1}")

                                # If this was the last attempt and it still failed
                                if render_attempt == max_render_attempts - 1 and process.returncode != 0:
                                    logger.error(f"Scene {scene_number} still fails after {max_render_attempts} fix attempts")
                                    failed_scenes[scene_number] = {
                                        'scene': scene,
                                        'error': error_message
                                    }
                                    # Skip this scene but continue with the next
                                    continue

                            except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
                                logger.error(f"Error running Manim for Scene {scene_number} (attempt {render_attempt+1}): {str(e)}")
                                if render_attempt == max_render_attempts - 1:
                                    failed_scenes[scene_number] = {
                                        'scene': scene,
                                        'error': str(e)
                                    }
                                    # Skip this scene but continue with the next
                                    continue

                except Exception as e:
                    logger.error(f"Unexpected error validating Scene {scene_number}: {str(e)}")
                    # We'll still add the scene but log the error

            # If we reach here, either validation succeeded or we're not testing
            scene_codes[scene_number] = scene_code
            logger.info(f"Successfully generated code for Scene {scene_number}")

        # Combine all successful scenes into a single file
        combined_code = self._assemble_scene_codes(theorem_name, scene_codes)

        # Save debug information if output_dir is provided
        if output_dir:
            debug_dir = os.path.join(output_dir, "debug")
            os.makedirs(debug_dir, exist_ok=True)

            with open(os.path.join(debug_dir, "combined_code.py"), "w") as f:
                f.write(combined_code)

            with open(os.path.join(debug_dir, "scene_generation_status.json"), "w") as f:
                status = {
                    "successful_scenes": list(scene_codes.keys()),
                    "failed_scenes": list(failed_scenes.keys())
                }
                json.dump(status, f, indent=2)

        logger.info(f"Generated combined Manim code with {len(scene_codes)} successful scenes")
        logger.info(f"Failed to generate {len(failed_scenes)} scenes")

        return combined_code

    def _attempt_to_fix_scene(self, theorem_name, scene, scene_number, scene_code, error_message, max_fix_attempts=3, output_dir=None):
        """Try multiple times to fix a scene until it works or we reach max attempts."""
        for attempt in range(max_fix_attempts):
            logger.info(f"Attempting to fix Scene {scene_number} (attempt {attempt+1}/{max_fix_attempts})")

            # Try to fix the scene
            fixed_code = self.fix_scene_code(
                theorem_name,
                scene,
                scene_number,
                scene_code,  # Always include the current code
                error_message,
                max_attempts=1,  # We're manually handling retries here
                output_dir=output_dir
            )

            if not fixed_code:
                logger.warning(f"Could not generate fix for Scene {scene_number} on attempt {attempt+1}")
                continue

            # Test if the fix works
            success = self._test_scene_syntax(fixed_code)
            if success:
                logger.info(f"Successfully fixed Scene {scene_number} on attempt {attempt+1}")
                return fixed_code

            # If fix didn't work, update error message and try again
            error_message = f"Fix attempt {attempt+1} failed. Previous code:\n{fixed_code}"
            # Use the fixed code as base for next attempt, even if it's still broken
            scene_code = fixed_code

        # If we reach here, all fix attempts failed
        logger.error(f"Failed to fix Scene {scene_number} after {max_fix_attempts} attempts")
        return None

    def _test_scene_syntax(self, scene_code):
        """Test if a scene's code has valid Python syntax."""
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp:
                temp_path = temp.name
                content = f"""from manim import *

# Constants for frame dimensions
config.frame_height = 8
config.frame_width = 14

{scene_code}

if __name__ == "__main__":
    pass
"""
                temp.write(content.encode('utf-8'))

            # Test compile
            import subprocess
            cmd = ["python", "-m", "py_compile", temp_path]
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Clean up
            try:
                os.unlink(temp_path)
            except:
                pass

            return process.returncode == 0
        except Exception as e:
            logger.error(f"Error testing scene syntax: {str(e)}")
            return False

    def generate_scene_code(self, theorem_name, theorem_description, scene, scene_number, output_dir=None):
        """Generate Manim code for a single scene."""
        # Generate the prompt for this specific scene
        prompt = get_single_scene_coding_prompt(
            theorem_name,
            theorem_description,
            scene,
            scene_number
        )

        # Get response from the model
        response = self.client.generate_response(prompt, max_tokens=8000, temperature=0.0)

        # Save the raw response for debugging if output_dir is provided
        if output_dir:
            debug_dir = os.path.join(output_dir, "debug", "scenes")
            os.makedirs(debug_dir, exist_ok=True)

            with open(os.path.join(debug_dir, f"scene_{scene_number}_response.txt"), "w") as f:
                f.write(response)

        # Extract the Python code
        code = self._extract_python_code(response)

        if not code:
            logger.error(f"No Python code found in the response for Scene {scene_number}")
            return None

        logger.info(f"Generated code for Scene {scene_number} ({len(code.split())} words)")
        return code

    def fix_code(self, theorem_name, scene_plan, manim_code, error_message, max_attempts=5, output_dir=None):
        """Fix errors in the generated Manim code by identifying and fixing problematic scenes."""
        logger.info(f"Attempting to fix Manim code for {theorem_name}")

        # Check for common errors that might need a global fix
        if self._is_common_global_error(error_message):
            logger.info(f"Detected common global error. Applying global fix...")
            fixed_code = self._apply_global_fix(manim_code, error_message)
            if fixed_code:
                logger.info(f"Successfully applied global fix")
                return fixed_code

        # Parse the error message to identify the problematic scene class
        scene_class, line_number = self._identify_problematic_scene(manim_code, error_message)

        if not scene_class:
            logger.warning("Could not identify the problematic scene. Attempting to fix the entire code.")
            # Fall back to the original approach if we can't identify the scene
            return self._fix_entire_code(theorem_name, scene_plan, manim_code, error_message, max_attempts, output_dir)

        # Find the scene in the scene plan that corresponds to the problematic scene class
        scene_info = None
        scene_number = None

        # Handle case where scene_plan might be a string (error from main.py)
        if isinstance(scene_plan, str):
            logger.warning(f"Scene plan is a string, not a dictionary. Using generic scene info.")
            scene_info = {"title": scene_class, "description": "Scene with error"}
            scene_number = 1
        else:
            # Normal case: scene_plan is a list of dictionaries
            for i, scene in enumerate(scene_plan):
                potential_class_name = self._generate_class_name(scene.get('title', f'Scene{i+1}'), i+1)
                if potential_class_name == scene_class:
                    scene_info = scene
                    scene_number = i + 1
                    break

            # If we couldn't match by class name, try a more flexible approach
            if not scene_info:
                # Just use the scene at the appropriate index based on the class number in the name
                match = re.search(r'Scene(\d+)', scene_class)
                if match:
                    try:
                        idx = int(match.group(1)) - 1
                        if 0 <= idx < len(scene_plan):
                            scene_info = scene_plan[idx]
                            scene_number = idx + 1
                    except ValueError:
                        pass

            if not scene_info and len(scene_plan) > 0:
                logger.warning(f"Could not find scene info for class {scene_class}. Using first scene as fallback.")
                scene_info = scene_plan[0]
                scene_number = 1

        if not scene_info:
            logger.warning(f"Could not find any scene info. Attempting to fix the entire code.")
            return self._fix_entire_code(theorem_name, scene_plan, manim_code, error_message, max_attempts, output_dir)

        # Extract the code for the problematic scene
        scene_code = self._extract_scene_code(manim_code, scene_class)

        if not scene_code:
            logger.warning(f"Could not extract code for scene class {scene_class}. Attempting to fix the entire code.")
            return self._fix_entire_code(theorem_name, scene_plan, manim_code, error_message, max_attempts, output_dir)

        # Fix the problematic scene
        fixed_scene_code = self.fix_scene_code(
            theorem_name,
            scene_info,
            scene_number,
            scene_code,
            error_message,
            max_attempts,
            output_dir
        )

        if not fixed_scene_code:
            logger.error(f"Failed to fix scene {scene_class} after {max_attempts} attempts")
            return None

        # Replace the problematic scene in the original code
        fixed_code = self._replace_scene_code(manim_code, scene_class, fixed_scene_code)

        # Ensure we have the necessary imports
        fixed_code = self._ensure_imports(fixed_code, error_message)

        logger.info(f"Successfully fixed scene {scene_class}")
        return fixed_code

    def _ensure_imports(self, code, error_message):
        """Ensure the code has all necessary imports based on the error message."""
        missing_imports = []

        # Check for common missing imports
        if "NameError: name 'math' is not defined" in error_message and "import math" not in code:
            missing_imports.append("import math")

        if "NameError: name 'np' is not defined" in error_message and "import numpy as np" not in code:
            missing_imports.append("import numpy as np")

        if "NameError: name 'random' is not defined" in error_message and "import random" not in code:
            missing_imports.append("import random")

        # Add the imports at the top of the file
        if missing_imports:
            # Find where the imports end
            lines = code.split('\n')
            last_import_line = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("import ") or line.strip().startswith("from "):
                    last_import_line = i

            # Insert the new imports after the last import
            for imp in missing_imports:
                lines.insert(last_import_line + 1, imp)
                last_import_line += 1

            return '\n'.join(lines)

        return code

    def _is_common_global_error(self, error_message):
        """Check if the error is a common one that requires a global fix."""
        common_errors = [
            ("NameError: name 'FRAME_HEIGHT' is not defined", True),
            ("NameError: name 'FRAME_WIDTH' is not defined", True),
            ("NameError: name 'PI' is not defined", True),
            ("NameError: name 'TAU' is not defined", True),
            ("NameError: name 'ORIGIN' is not defined", True),
            ("NameError: name 'UP' is not defined", True),
            ("NameError: name 'DOWN' is not defined", True),
            ("NameError: name 'LEFT' is not defined", True),
            ("NameError: name 'RIGHT' is not defined", True),
            ("NameError: name 'IN' is not defined", True),
            ("NameError: name 'OUT' is not defined", True),
            ("NameError: name 'UL' is not defined", True),
            ("NameError: name 'UR' is not defined", True),
            ("NameError: name 'DL' is not defined", True),
            ("NameError: name 'DR' is not defined", True),
            ("ImportError: cannot import name", True),
        ]

        for error_pattern, is_global in common_errors:
            if error_pattern in error_message:
                return is_global

        return False

    def _apply_global_fix(self, manim_code, error_message):
        """Apply a global fix for common errors."""
        # Fix for FRAME_HEIGHT, FRAME_WIDTH not defined
        if "NameError: name 'FRAME_HEIGHT' is not defined" in error_message or "NameError: name 'FRAME_WIDTH' is not defined" in error_message:
            # Check if we need to add config constants
            fixed_code = manim_code.replace(
                "from manim import *",
                "from manim import *\n\n# Constants for frame dimensions\nFRAME_HEIGHT = config.frame_height\nFRAME_WIDTH = config.frame_width"
            )
            return fixed_code

        # Fix for direction constants not defined
        direction_constants = ["ORIGIN", "UP", "DOWN", "LEFT", "RIGHT", "IN", "OUT", "UL", "UR", "DL", "DR"]
        for const in direction_constants:
            if f"NameError: name '{const}' is not defined" in error_message:
                # Check if we need to add imports
                if "import np" not in manim_code and "import numpy" not in manim_code:
                    fixed_code = manim_code.replace(
                        "from manim import *",
                        "from manim import *\nimport numpy as np"
                    )
                    return fixed_code

        # Fix for mathematical constants not defined
        math_constants = ["PI", "TAU", "E"]
        for const in math_constants:
            if f"NameError: name '{const}' is not defined" in error_message:
                fixed_code = manim_code.replace(
                    "from manim import *",
                    "from manim import *\nimport math\n\n# Math constants\nPI = math.pi\nTAU = 2 * math.pi\nE = math.e"
                )
                return fixed_code

        # Import errors
        if "ImportError: cannot import name" in error_message:
            # Extract what's being imported
            import_match = re.search(r"cannot import name '(\w+)'", error_message)
            if import_match:
                missing_import = import_match.group(1)
                fixed_code = manim_code.replace(
                    "from manim import *",
                    f"from manim import *\nfrom manim.constants import *  # Import additional constants"
                )
                return fixed_code

        return None

    def fix_scene_code(self, theorem_name, scene, scene_number, scene_code, error_message, max_attempts=5, output_dir=None):
        """Fix errors in a specific scene with improved error information."""
        logger.info(f"Attempting to fix Scene {scene_number} for {theorem_name}")

        # First, save the original error message and code to a debug file if output_dir is provided
        if output_dir:
            debug_dir = os.path.join(output_dir, "debug", "fixes")
            os.makedirs(debug_dir, exist_ok=True)

            # Save the original error
            with open(os.path.join(debug_dir, f"scene_{scene_number}_original_error.txt"), "w") as f:
                f.write(error_message)

            # Save the original code
            with open(os.path.join(debug_dir, f"scene_{scene_number}_original_code.py"), "w") as f:
                f.write(scene_code)

        # Create a standalone version of the code for easier debugging
        class_name = self._generate_class_name(scene.get('title', f'Scene{scene_number}'), scene_number)
        standalone_code = f"""from manim import *

# Constants for frame dimensions
config.frame_height = 8
config.frame_width = 14

{scene_code}

# This helps identify class name mismatches
# The scene class name should be: {class_name}
"""

        for attempt in range(max_attempts):
            logger.info(f"Fix attempt {attempt + 1}/{max_attempts} for Scene {scene_number}")

            # Generate the prompt for fixing this specific scene
            prompt = get_single_scene_fixing_prompt(
                theorem_name,
                scene,
                scene_number,
                standalone_code,  # Include the standalone version with imports
                error_message  # Include the full error message
            )

            # Get response from the model
            response = self.client.generate_response(prompt, max_tokens=10000, temperature=0.0)

            # Save the raw response for debugging if output_dir is provided
            if output_dir:
                debug_dir = os.path.join(output_dir, "debug", "fixes")
                os.makedirs(debug_dir, exist_ok=True)

                with open(os.path.join(debug_dir, f"scene_{scene_number}_fix_{attempt+1}.txt"), "w") as f:
                    f.write(response)

            # Extract the Python code
            fixed_code = self._extract_python_code(response)

            if not fixed_code:
                logger.warning(f"No Python code found in fix attempt {attempt + 1} for Scene {scene_number}")
                continue

            # Save the fixed code for debugging
            if output_dir:
                with open(os.path.join(debug_dir, f"scene_{scene_number}_fixed_{attempt+1}.py"), "w") as f:
                    f.write(fixed_code)

            logger.info(f"Generated fixed code for Scene {scene_number} ({len(fixed_code.split())} words)")

            # We need to extract just the scene class code, not the full file with imports
            # This makes sure we're not including imports twice when assembling the final code
            scene_class_code = self._extract_scene_class_code(fixed_code, class_name)

            if scene_class_code:
                logger.info(f"Extracted scene class code for {class_name}")
                return scene_class_code
            else:
                logger.warning(f"Could not extract scene class from fix. Using full code.")
                # As a fallback, try to remove just the imports
                lines = fixed_code.split('\n')
                non_import_lines = []
                for line in lines:
                    if not (line.startswith('import ') or line.startswith('from ') or
                            line.startswith('config.') or line.startswith('# Constants')):
                        non_import_lines.append(line)

                return '\n'.join(non_import_lines)

        logger.error(f"Failed to fix Scene {scene_number} after {max_attempts} attempts")
        return None

    def _extract_scene_class_code(self, code, class_name):
        """Extract just the scene class code from the full fixed code."""
        try:
            lines = code.split('\n')
            in_class = False
            class_lines = []
            indent_level = 0

            # Find the class definition
            for i, line in enumerate(lines):
                if line.strip().startswith(f"class {class_name}") or line.strip().startswith(f"class UnderstandingRightTriangles_Scene"):
                    in_class = True
                    class_lines.append(line)
                    # Determine indentation level from first line after class def
                    for j in range(i+1, len(lines)):
                        if lines[j].strip() and not lines[j].strip().startswith('#'):
                            indent_level = len(lines[j]) - len(lines[j].lstrip())
                            break
                elif in_class:
                    # Check if we've exited the class (new class or reduced indentation)
                    if line.strip().startswith('class ') or (line.strip() and not line.strip().startswith('#') and len(line) - len(line.lstrip()) < indent_level):
                        in_class = False
                    else:
                        class_lines.append(line)

            # Also include any helper functions defined before the class
            helper_functions = []
            in_helper = False
            for line in lines:
                if line.strip().startswith('def ') and not in_helper:
                    in_helper = True
                    helper_functions.append(line)
                elif in_helper:
                    if line.strip().startswith('class '):
                        in_helper = False
                    else:
                        helper_functions.append(line)

            # Combine helper functions and class code
            result = '\n'.join(helper_functions + [''] + class_lines)
            return result
        except Exception as e:
            logger.error(f"Error extracting scene class code: {str(e)}")
            return None

    def _fix_entire_code(self, theorem_name, scene_plan, manim_code, error_message, max_attempts=5, output_dir=None):
        """Fall back to fixing the entire code as a last resort."""
        logger.info(f"Attempting to fix entire code for {theorem_name}")

        for attempt in range(max_attempts):
            logger.info(f"Full code fix attempt {attempt + 1}/{max_attempts}")

            # Generate the prompt
            prompt = get_code_fixing_prompt(theorem_name, scene_plan[0], manim_code, error_message)

            # Get response from the model
            response = self.client.generate_response(prompt, max_tokens=32000, temperature=0.0)

            # Save the raw response for debugging if output_dir is provided
            if output_dir:
                debug_dir = os.path.join(output_dir, "debug")
                os.makedirs(debug_dir, exist_ok=True)

                with open(os.path.join(debug_dir, f"code_fixing_response_raw_{attempt+1}.txt"), "w") as f:
                    f.write(response)

            # Extract the Python code
            fixed_code = self._extract_python_code(response)

            if not fixed_code:
                logger.warning(f"No Python code found in fix attempt {attempt + 1}")
                continue

            logger.info(f"Generated fixed code ({len(fixed_code.split())} words)")

            # Return the fixed code (it will be tested by the caller)
            return fixed_code

        logger.error(f"Failed to fix code after {max_attempts} attempts")
        return None

    def _identify_problematic_scene(self, manim_code, error_message):
        """Parse the error message to identify the problematic scene class and line number."""
        # First try to extract the file path and line number where the error occurred
        file_line_pattern = r"([^\s]+\.py):(\d+)"
        file_line_matches = re.findall(file_line_pattern, error_message)

        # Try a more detailed pattern to extract file path, line number from traceback
        if not file_line_matches:
            file_line_pattern = r"(/[^\s]+\.py)\:?(\d+)"
            file_line_matches = re.findall(file_line_pattern, error_message)

        # Newer error traceback format often includes the code line itself
        code_line_pattern = r"│\s*❱\s*(\d+)\s*│.*?│\s*(.*?)\s*│"
        code_line_matches = re.findall(code_line_pattern, error_message, re.DOTALL)

        # Look for class mentions in the error
        class_pattern = r"in\s+(\w+)"
        class_matches = re.findall(class_pattern, error_message)

        # Extract explicit class names from code lines in the traceback
        explicit_class_pattern = r"class\s+(\w+)[\(:]"
        explicit_class_matches = re.findall(explicit_class_pattern, error_message)

        # General line number pattern
        line_pattern = r"line\s+(\d+)"
        line_matches = re.findall(line_pattern, error_message)

        # Initialize variables
        scene_class = None
        line_number = None

        # Try to identify line number from various patterns
        if code_line_matches:
            try:
                line_number = int(code_line_matches[0][0])
            except (ValueError, IndexError):
                pass

        if not line_number and file_line_matches:
            try:
                line_number = int(file_line_matches[0][1])
            except (ValueError, IndexError):
                pass

        if not line_number and line_matches:
            try:
                line_number = int(line_matches[0])
            except (ValueError, IndexError):
                pass

        # Try to identify class name from various patterns
        if explicit_class_matches:
            for match in explicit_class_matches:
                if match != "Scene" and ("Scene" in match or match[0].isupper()):
                    scene_class = match
                    break

        if not scene_class and class_matches:
            for match in class_matches:
                if match != "Scene" and match != "construct" and match != "render" and (match[0].isupper() or "Scene" in match):
                    scene_class = match
                    break

        # Look for class definition in code directly from the error message
        if not scene_class:
            # If we have a line from the traceback, look for class references
            for line in error_message.split('\n'):
                if "class" in line and "Scene" in line:
                    class_match = re.search(r"class\s+(\w+)", line)
                    if class_match:
                        scene_class = class_match.group(1)
                        break

        # If we still couldn't find a scene class by the error message, try to guess based on the line number
        if not scene_class and line_number:
            scene_class = self._guess_scene_from_line_number(manim_code, line_number)

        # Last resort: If error is in the first scene, just return the first scene class
        if not scene_class and "manim_code.py" in error_message:
            # Extract all scene classes from the code
            class_pattern = r"class\s+(\w+)\s*\(\s*Scene\s*\)"
            all_classes = re.findall(class_pattern, manim_code)
            if all_classes:
                scene_class = all_classes[0]  # Take the first class as a guess

        logger.info(f"Identified problematic scene: {scene_class} at line {line_number}")
        return scene_class, line_number

    def _guess_scene_from_line_number(self, manim_code, line_number):
        """Try to guess the scene class based on the line number in the error."""
        lines = manim_code.split('\n')

        # Ensure line_number is within bounds
        if not line_number or line_number > len(lines):
            # If line number is out of bounds, return the first scene class as a fallback
            class_pattern = r"class\s+(\w+)\s*\(\s*Scene\s*\)"
            all_classes = re.findall(class_pattern, manim_code)
            return all_classes[0] if all_classes else None

        # Look for the nearest class definition before the error line
        class_pattern = r"class\s+(\w+)\s*\(\s*Scene\s*\)"

        for i in range(min(line_number - 1, len(lines) - 1), -1, -1):
            match = re.search(class_pattern, lines[i])
            if match:
                return match.group(1)

        # If we couldn't find a class definition before the error line,
        # it might be in a method of the last class, so find the last class
        all_classes = re.findall(class_pattern, manim_code)
        return all_classes[-1] if all_classes else None

    def _extract_scene_code(self, manim_code, scene_class):
        """Extract the code for a specific scene class."""
        lines = manim_code.split('\n')

        # Find the start of the scene class
        start_line = -1
        for i, line in enumerate(lines):
            if re.search(f"class\s+{scene_class}\s*\(", line):
                start_line = i
                break

        if start_line == -1:
            logger.error(f"Could not find start of scene class {scene_class}")
            return None

        # Find the end of the scene class (next class definition or end of file)
        end_line = len(lines)
        for i in range(start_line + 1, len(lines)):
            if re.search(r"class\s+\w+\s*\(", lines[i]):
                end_line = i
                break

        # Extract the scene code
        scene_code = '\n'.join(lines[start_line:end_line])
        return scene_code

    def _replace_scene_code(self, manim_code, scene_class, fixed_scene_code):
        """Replace a scene class in the original code with the fixed version."""
        lines = manim_code.split('\n')

        # Find the start of the scene class
        start_line = -1
        for i, line in enumerate(lines):
            if re.search(f"class\s+{scene_class}\s*\(", line):
                start_line = i
                break

        if start_line == -1:
            logger.error(f"Could not find start of scene class {scene_class}")
            return manim_code

        # Find the end of the scene class (next class definition or end of file)
        end_line = len(lines)
        for i in range(start_line + 1, len(lines)):
            if re.search(r"class\s+\w+\s*\(", lines[i]):
                end_line = i
                break

        # Replace the scene code
        fixed_scene_lines = fixed_scene_code.split('\n')

        # Check if the fixed scene code has the correct class name
        class_match = re.search(r"class\s+(\w+)\s*\(", fixed_scene_lines[0])
        if class_match and class_match.group(1) != scene_class:
            # Fix the class name in the fixed code
            fixed_scene_lines[0] = fixed_scene_lines[0].replace(class_match.group(1), scene_class)

        # Combine everything
        new_lines = lines[:start_line] + fixed_scene_lines + lines[end_line:]
        return '\n'.join(new_lines)

    def _assemble_scene_codes(self, theorem_name, scene_codes):
        """Combine individual scene codes into a complete Manim file with proper imports."""
        if not scene_codes:
            logger.error("No successful scenes to assemble")
            return None
    
        # Start with the standard imports
        imports = [
            "from manim import *",
            "import numpy as np",
            "import math",  # Add math import to avoid common errors
            "import random"  # Add random import to avoid common errors
        ]
    
        # Scan the code for additional required imports
        for scene_number in sorted(scene_codes.keys()):
            scene_code = scene_codes[scene_number]
            if "import" in scene_code:
                lines = scene_code.split('\n')
                for line in lines:
                    if line.strip().startswith("import ") or line.strip().startswith("from "):
                        if line.strip() not in imports and "manim" not in line:
                            imports.append(line.strip())
    
        # Add imports as a group
        combined_code = "\n".join(imports) + "\n\n"
    
        # Add each scene's class directly - NO ATTEMPT TO EXTRACT HELPERS OR MODIFY
        # This is the key change - we're not trying to be clever with helper functions
        # Instead, we just add each class directly with its original indentation
        for scene_number in sorted(scene_codes.keys()):
            scene_code = scene_codes[scene_number]
            
            # Extract just the class definition
            class_lines = []
            in_class = False
            
            for line in scene_code.split('\n'):
                # Start collecting at class definition
                if line.strip().startswith('class '):
                    in_class = True
                    
                # If we're in a class, add the line
                if in_class:
                    class_lines.append(line)
            
            # Add the class code if we found any
            if class_lines:
                combined_code += '\n'.join(class_lines) + '\n\n'
    
        # Add main block
        combined_code += "if __name__ == \"__main__\":\n"
        combined_code += "    # This will be handled by the system\n"
        combined_code += "    pass\n"
    
        return combined_code

    def _generate_class_name(self, scene_title, scene_number):
        """Generate a class name based on scene title and number."""
        # Remove non-alphanumeric characters and replace spaces with underscores
        clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', scene_title)
        clean_title = clean_title.replace(' ', '_')

        # Ensure the class name starts with a capital letter
        if clean_title and clean_title[0].islower():
            clean_title = clean_title[0].upper() + clean_title[1:]

        # If the title is empty, use Scene{number}
        if not clean_title:
            return f"Scene{scene_number}"

        return f"{clean_title}_Scene{scene_number}"

    def _extract_python_code(self, response):
        """Extract Python code from the model's response."""
        # Method 1: Look for Python code blocks with triple backticks
        pattern = r"```python(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            # Join all code blocks if multiple are found
            return "\n\n".join(match.strip() for match in matches)

        # Method 2: Fallback - try to find code without language specification
        pattern = r"```(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            # Join all code blocks if multiple are found
            return "\n\n".join(match.strip() for match in matches)

        # Method 3: Extreme fallback - look for lines that appear to be Python code
        # This is risky but might help in some cases
        lines = response.split('\n')
        code_lines = []
        in_code_section = False

        for line in lines:
            if line.strip().startswith('from manim import') or line.strip().startswith('import manim'):
                in_code_section = True
                code_lines.append(line)
            elif in_code_section:
                # Keep adding lines that look like Python code
                if line.strip() and not line.startswith('#') and not line.startswith('```'):
                    code_lines.append(line)

        if code_lines:
            return '\n'.join(code_lines)

        return None
    def render_and_combine_videos(output_dir):
        """Render all scenes and then combine the videos into a single file."""
        
        # Path to scene files
        temp_dir = os.path.join(output_dir, "temp_scenes")
        
        if not os.path.exists(temp_dir):
            print(f"Temp scenes directory does not exist: {temp_dir}")
            return False
        
        # Find all scene files
        scene_files = []
        for file in sorted(os.listdir(temp_dir)):
            if file.startswith("scene_") and file.endswith("_test.py"):
                scene_files.append(os.path.join(temp_dir, file))
        
        if not scene_files:
            print("No scene files found to render")
            return False
        
        # Initialize manim executor
        media_dir = os.path.join(output_dir, "media")
        manim_executor = ManimExecutor(output_dir=media_dir)
        
        # Render each scene
        for scene_file in scene_files:
            with open(scene_file, "r") as f:
                scene_code = f.read()
            
            # Extract the class name
            import re
            class_match = re.search(r"class\s+(\w+)\s*\(Scene\):", scene_code)
            if class_match:
                class_name = class_match.group(1)
                print(f"Rendering scene: {class_name}")
                
                # Render the scene
                success, error, output_files = manim_executor.execute_code(
                    scene_code,
                    filename=scene_file,
                    scene_names=[class_name]
                )
                
                if success:
                    print(f"Successfully rendered scene: {class_name}")
                else:
                    print(f"Failed to render scene {class_name}: {error}")
        
        # Now combine the rendered videos
        media_dir = os.path.join(output_dir, "media", "videos")
        
        if not os.path.exists(media_dir):
            print(f"Media directory does not exist: {media_dir}")
            return False
            
        # Create a list file for ffmpeg
        video_files = []
        for subdir in sorted(os.listdir(media_dir)):
            subdir_path = os.path.join(media_dir, subdir)
            if os.path.isdir(subdir_path):
                for file in os.listdir(subdir_path):
                    if file.endswith(".mp4"):
                        video_files.append(os.path.join(subdir_path, file))
        
        if not video_files:
            print("No video files found to combine")
            return False
        
        # Create a temporary file list for ffmpeg
        with open(os.path.join(output_dir, "video_list.txt"), "w") as f:
            for video_file in video_files:
                f.write(f"file '{video_file}'\n")
        
        # Output combined video file
        output_file = os.path.join(output_dir, "combined_video.mp4")
        
        # Use ffmpeg to concatenate the videos
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", os.path.join(output_dir, "video_list.txt"),
            "-c", "copy",
            output_file
        ]
        
        try:
            import subprocess
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Successfully combined videos into {output_file}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error combining videos: {e.stderr.decode()}")
            return False