# Original prompt templates (kept for backward compatibility)
CODING_PROMPT_TEMPLATE = """
You are an expert Manim (Community Edition) developer. Generate executable Manim code implementing animations as specified in the scene plan below. The code should create a video that explains the theorem in a clear, visually appealing way.

THEOREM INFORMATION:
Theorem Name: {theorem_name}
Theorem Description: {theorem_description}

SCENE PLAN:
{scene_plan}

SPECIFIC REQUIREMENTS AND RESTRICTIONS:
1. Use Manim Community Edition syntax (not legacy Manim).
2. Create a single Python file with all necessary classes and imports.
3. Each scene should be a separate class inheriting from Scene.
4. Include detailed comments explaining the code.
5. DO NOT use MathTex or Tex classes - use Text() class only for all text/formulas.
6. DO NOT use ImageMobject or load any external images.
7. DO NOT try to load images from URLs or external sources.
8. Use ONLY geometric shapes, lines, Text, and other built-in Manim objects.
9. ALWAYS properly close ALL parentheses, brackets, and quotes.
10. Keep the code simple and focus on core Manim functionality.
11. Double-check all string literals to ensure they are properly terminated.
12. Ensure all animation code is complete and doesn't cut off mid-statement.

EXAMPLE MANIM CODE FORMAT:
```python
from manim import *

class Scene1_Introduction(Scene):
    def construct(self):
        # Title
        title = Text("Pythagorean Theorem", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))

        # Triangle
        triangle = Polygon(ORIGIN, RIGHT*3, UP*4, color=WHITE)

        # Labels using Text instead of MathTex
        a_label = Text("a", font_size=24, color=BLUE)
        a_label.next_to(triangle, DOWN)

        self.play(Create(triangle))
        self.play(Write(a_label))

class Scene2_Explanation(Scene):
    def construct(self):
        # More code...
        pass

if __name__ == "__main__":
    # This will be handled by the system
    pass
```

IMPORTANT:
- Your code must be complete, executable, and error-free
- DO NOT use MathTex or any LaTeX-based objects
- DO NOT try to load external images
- FOCUS on basic geometric animations
- CHECK all parentheses and quotes are properly closed
- IMPLEMENT all scenes from the scene plan
"""

# New template for single scene generation
SINGLE_SCENE_CODING_TEMPLATE = """
You are an expert Manim (Community Edition) developer. Generate executable Manim code implementing a SINGLE SCENE as specified in the scene plan below. The code should create a scene that explains one aspect of the theorem in a clear, visually appealing way.

THEOREM INFORMATION:
Theorem Name: {theorem_name}
Theorem Description: {theorem_description}

SCENE INFORMATION:
Scene Number: {scene_number}
Scene Title: {scene_title}
Scene Purpose: {scene_purpose}
Scene Description: {scene_description}
Scene Layout: {scene_layout}
Scene Narration: {scene_narration}

SPECIFIC REQUIREMENTS AND RESTRICTIONS:
1. Use Manim Community Edition syntax (not legacy Manim).
2. Create ONLY ONE scene class inheriting from Scene.
3. Include detailed comments explaining the code.
4. DO NOT use MathTex or Tex classes - use Text() class only for all text/formulas.
5. DO NOT use ImageMobject or load any external images.
6. DO NOT try to load images from URLs or external sources.
7. Use ONLY geometric shapes, lines, Text, and other built-in Manim objects.
8. ALWAYS properly close ALL parentheses, brackets, and quotes.
9. Keep the code simple and focus on core Manim functionality.
10. Double-check all string literals to ensure they are properly terminated.
11. Ensure all animation code is complete and doesn't cut off mid-statement.
12. NAME THE CLASS using the scene title in CamelCase followed by "_Scene{scene_number}".
13. IMPORTANT: DO NOT use constants like FRAME_HEIGHT, FRAME_WIDTH, ORIGIN, UP, DOWN, LEFT, RIGHT directly.
    - For screen dimensions, use config.frame_height and config.frame_width
    - For directions, use UP, RIGHT, etc. only after "from manim import *"
    - If you need mathematical constants, import them from math (PI = math.pi)
    - Example: margin = 0.1 * config.frame_height  # NOT: margin = 0.1 * FRAME_HEIGHT

EXAMPLE MANIM CODE FORMAT:
```python
from manim import *

class Introduction_Scene1(Scene):
    def construct(self):
        # Title
        title = Text("Pythagorean Theorem", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))

        # Get screen dimensions using config
        screen_height = config.frame_height
        screen_width = config.frame_width

        # Create margin based on screen size
        margin = 0.1 * screen_height

        # Triangle - using direction constants imported from manim
        triangle = Polygon(ORIGIN, RIGHT*3, UP*4, color=WHITE)

        # Labels using Text instead of MathTex
        a_label = Text("a", font_size=24, color=BLUE)
        a_label.next_to(triangle, DOWN)

        self.play(Create(triangle))
        self.play(Write(a_label))
        self.wait(2)
```

IMPORTANT:
- Generate ONLY ONE scene class
- Your code must be complete, executable, and error-free
- Include the full class with the proper name format
- DO NOT use MathTex or any LaTeX-based objects
- DO NOT try to load external images
- FOCUS on basic geometric animations
- CHECK all parentheses and quotes are properly closed
"""

# Original code fixing template
CODE_FIXING_PROMPT_TEMPLATE = """
You are an expert Manim developer specializing in debugging and error resolution. Based on the provided implementation plan and Manim code, analyze the error message to provide a comprehensive fix.

Theorem Name: {theorem_name}

Scene Plan for this section:
{scene_plan}

Manim Code that has an error:
```python
{manim_code}
```

Error Message:
{error_message}

REQUIREMENTS AND RESTRICTIONS:
1. Provide complete error analysis with specific line numbers.
2. Include exact instructions for every code change.
3. Explain why the error occurred in plain language.
4. DO NOT use MathTex or Tex classes - use Text() class only for all text/formulas.
5. DO NOT use ImageMobject or load any external images.
6. DO NOT try to load images from URLs or external sources.
7. Use ONLY geometric shapes, lines, Text, and other built-in Manim objects.
8. ALWAYS properly close ALL parentheses, brackets, and quotes.
9. Keep the code simple and focus on core Manim functionality.
10. Create a COMPLETE, WORKING solution that includes ALL necessary imports.
11. Your solution MUST start with "from manim import *" at the beginning.
12. Make sure the scene inherits from Scene and includes a construct method.
13. Double-check all string literals to ensure they are properly terminated.

Your response MUST include a complete corrected version of the code that runs without errors.

EXAMPLE OF CORRECTLY FIXED CODE:
```python
from manim import *

class PythagoreanTheoremIntro(Scene):
    def construct(self):
        # Title
        title = Text("Pythagorean Theorem", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))

        # Create a right triangle
        triangle = Polygon(ORIGIN, RIGHT*3, UP*4, color=WHITE)

        # Show formula
        formula = Text("a² + b² = c²", font_size=36)
        formula.next_to(triangle, DOWN, buff=0.5)

        self.play(Create(triangle))
        self.play(Write(formula))
        self.wait(2)
```
"""

# New template for fixing a single scene
SINGLE_SCENE_FIXING_TEMPLATE = """
You are an expert Manim developer specializing in debugging and error resolution. Based on the provided implementation plan and Manim code, analyze the error message to provide a comprehensive fix for this SINGLE SCENE.

Theorem Name: {theorem_name}

SCENE INFORMATION:
Scene Number: {scene_number}
Scene Title: {scene_title}
Scene Purpose: {scene_purpose}
Scene Description: {scene_description}
Scene Layout: {scene_layout}
Scene Narration: {scene_narration}

Manim Scene Code that has an error:
```python
{scene_code}
```

Error Message:
{error_message}

REQUIREMENTS AND RESTRICTIONS:
1. Provide complete error analysis with specific line numbers.
2. Include exact instructions for every code change.
3. Explain why the error occurred in plain language.
4. DO NOT use MathTex or Tex classes - use Text() class only for all text/formulas.
5. DO NOT use ImageMobject or load any external images.
6. DO NOT try to load images from URLs or external sources.
7. Use ONLY geometric shapes, lines, Text, and other built-in Manim objects.
8. ALWAYS properly close ALL parentheses, brackets, and quotes.
9. Keep the code simple and focus on core Manim functionality.
10. CRITICAL: Your solution MUST be a COMPLETE, COMPILABLE file with imports.
11. Your solution MUST include the exact class name as expected: {scene_title}_Scene{scene_number}.
12. Make sure the scene inherits from Scene and includes a construct method.
13. Double-check all string literals to ensure they are properly terminated.
14. IMPORTANT FIX FOR COMMON ERRORS:
    - Replace FRAME_HEIGHT with config.frame_height
    - Replace FRAME_WIDTH with config.frame_width
    - If constants like UP, DOWN, RIGHT, LEFT are undefined, they should be available after "from manim import *"
    - If mathematical constants are missing, use math.pi instead of PI, 2*math.pi instead of TAU, etc.
    - Make sure imports include "from manim import *" at the top of the file
15. Do not include any code at the top level outside of imports, functions, and classes - all code must be properly contained within functions or methods.
16. Your solution must start with "from manim import *" and then include the entire scene class.

Your response MUST include a complete correct version of the code that runs without errors.

CRITICAL: DO NOT SKIP OR ABBREVIATE ANY PART OF THE CODE. Include ALL helper functions and the ENTIRE scene class with EVERY method fully implemented. Do not use ellipses (...) or comments like "rest of code unchanged".

EXAMPLE OF CORRECTLY FIXED CODE:
```python
from manim import *

# Helper function for creating triangles
def create_triangle(point1, point2, point3, color=WHITE):
    return Polygon(point1, point2, point3, color=color)

class PythagoreanTheorem_Scene1(Scene):
    def construct(self):
        # Access screen dimensions using config
        screen_height = config.frame_height
        margin = 0.1 * screen_height

        # Title
        title = Text("Pythagorean Theorem", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))

        # Create a right triangle - using ORIGIN, RIGHT, UP from manim
        triangle = Polygon(ORIGIN, RIGHT*3, UP*4, color=WHITE)

        # Show formula
        formula = Text("a² + b² = c²", font_size=36)
        formula.next_to(triangle, DOWN, buff=0.5)

        self.play(Create(triangle))
        self.play(Write(formula))
        self.wait(2)
```

Your response MUST include a complete corrected version of the scene code that runs without errors.

EXAMPLE OF CORRECTLY FIXED CODE:
```python
from manim import *

class PythagoreanTheorem_Scene1(Scene):
    def construct(self):
        # Access screen dimensions using config
        screen_height = config.frame_height
        margin = 0.1 * screen_height

        # Title
        title = Text("Pythagorean Theorem", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))

        # Create a right triangle - using ORIGIN, RIGHT, UP from manim
        triangle = Polygon(ORIGIN, RIGHT*3, UP*4, color=WHITE)

        # Show formula
        formula = Text("a² + b² = c²", font_size=36)
        formula.next_to(triangle, DOWN, buff=0.5)

        self.play(Create(triangle))
        self.play(Write(formula))
        self.wait(2)
```
"""

def get_coding_prompt(theorem_name, theorem_description, scene_plan):
    """Generate a prompt for the coding agent."""
    # Convert scene plan to formatted string
    scene_plan_str = ""
    for i, scene in enumerate(scene_plan, 1):
        scene_plan_str += f"[Scene {i}]\n"
        scene_plan_str += f"Title: {scene.get('title', '')}\n"
        scene_plan_str += f"Purpose: {scene.get('purpose', '')}\n"
        scene_plan_str += f"Description: {scene.get('description', '')}\n"
        scene_plan_str += f"Layout: {scene.get('layout', '')}\n"
        scene_plan_str += f"Narration: {scene.get('narration', '')}\n\n"

    return CODING_PROMPT_TEMPLATE.format(
        theorem_name=theorem_name,
        theorem_description=theorem_description,
        scene_plan=scene_plan_str
    )

def get_single_scene_coding_prompt(theorem_name, theorem_description, scene, scene_number):
    """Generate a prompt for coding a single scene."""
    # Extract scene information
    scene_title = scene.get('title', f'Scene{scene_number}')
    scene_purpose = scene.get('purpose', '')
    scene_description = scene.get('description', '')
    scene_layout = scene.get('layout', '')
    scene_narration = scene.get('narration', '')

    return SINGLE_SCENE_CODING_TEMPLATE.format(
        theorem_name=theorem_name,
        theorem_description=theorem_description,
        scene_number=scene_number,
        scene_title=scene_title,
        scene_purpose=scene_purpose,
        scene_description=scene_description,
        scene_layout=scene_layout,
        scene_narration=scene_narration
    )

def get_code_fixing_prompt(theorem_name, scene_plan, manim_code, error_message):
    """Generate a prompt for fixing code errors."""
    # Format scene plan
    scene_plan_str = f"Title: {scene_plan.get('title', '')}\n"
    scene_plan_str += f"Purpose: {scene_plan.get('purpose', '')}\n"
    scene_plan_str += f"Description: {scene_plan.get('description', '')}\n"
    scene_plan_str += f"Layout: {scene_plan.get('layout', '')}\n"
    scene_plan_str += f"Narration: {scene_plan.get('narration', '')}\n"

    return CODE_FIXING_PROMPT_TEMPLATE.format(
        theorem_name=theorem_name,
        scene_plan=scene_plan_str,
        manim_code=manim_code,
        error_message=error_message
    )

def get_single_scene_fixing_prompt(theorem_name, scene, scene_number, scene_code, error_message):
    """Generate a prompt for fixing errors in a single scene."""
    # Extract scene information
    scene_title = scene.get('title', f'Scene{scene_number}')
    scene_purpose = scene.get('purpose', '')
    scene_description = scene.get('description', '')
    scene_layout = scene.get('layout', '')
    scene_narration = scene.get('narration', '')

    return SINGLE_SCENE_FIXING_TEMPLATE.format(
        theorem_name=theorem_name,
        scene_number=scene_number,
        scene_title=scene_title,
        scene_purpose=scene_purpose,
        scene_description=scene_description,
        scene_layout=scene_layout,
        scene_narration=scene_narration,
        scene_code=scene_code,
        error_message=error_message
    )
