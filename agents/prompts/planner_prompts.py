PLANNER_PROMPT_TEMPLATE = """
You are an expert in video production, instructional design, and {topic}. Please design a high-quality video to provide in-depth explanation on {topic}.

Video Overview:

Topic: {topic}  
Description: {description}

Scene Breakdown:

Plan individual scenes. For each scene please provide the following:

- Scene Title: Short, descriptive title (2-5 words).
- Scene Purpose: Objective of this scene. How does it connect to previous scenes?
- Scene Description: Detailed description of scene content.
- Scene Layout: Detailed description of the spatial layout concept. Consider safe area margins and minimum spacing between objects.
- Narration Script: Word-for-word narration that will be spoken during this scene.

Please generate the scene plan for the video in the following format:

SCENE PLAN BEGIN:
[Scene 1]
Title: Introduction to {topic}
Purpose: To introduce the theorem and its importance
Description: Start with the formal statement of the theorem, then provide historical context. Explain why this theorem is important and what problems it solves.
Layout: Center the theorem statement with a title above. Use decorative elements on the sides to emphasize importance. Consider showing relevant historical figure if applicable.
Narration: "Welcome to our exploration of {topic}. This theorem, which states that [theorem statement], is a fundamental concept in [field]. First introduced by [person] in [year], it has become essential for understanding [applications]."

[Scene 2]
...continue with all scenes...

SCENE PLAN END:

Remember to make the explanation rigorous yet intuitive, with visuals that enhance understanding. Create a sequence of scenes that builds progressively from basic concepts to the full theorem understanding.
"""

def get_planner_prompt(topic, description):
    """Generate a prompt for the planner agent."""
    return PLANNER_PROMPT_TEMPLATE.format(
        topic=topic,
        description=description
    )
