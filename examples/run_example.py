#!/usr/bin/env python3
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import main

# Example theorems with descriptions
EXAMPLES = {
    "Pythagorean Theorem": "In a right-angled triangle, the square of the length of the hypotenuse is equal to the sum of the squares of the lengths of the other two sides.",
    
    "Law of Conservation of Energy": "Energy cannot be created or destroyed; it can only be transferred or changed from one form to another.",
    
    "Central Limit Theorem": "Given certain conditions, the arithmetic mean of a sufficiently large number of iterates of independent random variables will be approximately normally distributed, regardless of the underlying distribution.",
    
    "Octet Rule in Chemistry": "Atoms tend to gain, lose, or share electrons until they have eight electrons in their valence shell, which gives them the same electron configuration as a noble gas."
}

def run_example(example_name):
    """Run TheoremExplainAgent on a specific example."""
    if example_name not in EXAMPLES:
        print(f"Example '{example_name}' not found. Available examples: {', '.join(EXAMPLES.keys())}")
        return
    
    theorem_name = example_name
    theorem_description = EXAMPLES[example_name]
    
    print(f"Running TheoremExplainAgent for: {theorem_name}")
    print(f"Description: {theorem_description}")
    print("=" * 80)
    
    # Create output directory for this example
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", theorem_name.replace(" ", "_"))
    os.makedirs(output_dir, exist_ok=True)
    
    result = main(theorem_name, theorem_description, output_dir)
    
    # Save the result
    with open(os.path.join(output_dir, "result.json"), "w") as f:
        json.dump(result, f, indent=2)
    
    if result["success"]:
        print(f"Successfully created explanation video: {result['final_video']}")
    else:
        print(f"Failed to create explanation video: {result['error']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run TheoremExplainAgent examples")
    parser.add_argument("example", choices=list(EXAMPLES.keys()) + ["all"], help="Example to run, or 'all' for all examples")
    
    args = parser.parse_args()
    
    if args.example == "all":
        for example in EXAMPLES:
            run_example(example)
    else:
        run_example(args.example)
