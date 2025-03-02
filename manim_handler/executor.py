import os
import re
import logging
import subprocess
import tempfile
from pathlib import Path
import shutil
import glob

from config import MANIM_QUALITY, MANIM_OUTPUT_DIR

logger = logging.getLogger(__name__)

class ManimExecutor:
    def __init__(self, output_dir=None):
        """Initialize the Manim executor."""
        self.output_dir = output_dir or MANIM_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Initialized ManimExecutor with output directory: {self.output_dir}")
    
    def execute_code(self, manim_code, filename=None, scene_names=None):
        """Execute the generated Manim code."""
        if filename is None:
            # Create a temporary file for the script
            temp_dir = tempfile.mkdtemp()
            filename = os.path.join(temp_dir, "manim_script.py")
        
        try:
            # Write the code to a Python file
            with open(filename, "w") as file:
                file.write(manim_code)
            
            logger.info(f"Wrote Manim code to {filename}")
            
            # Extract scene classes from the code if not provided
            if scene_names is None:
                scene_names = self._extract_scene_classes(manim_code)
                
            if not scene_names:
                logger.error("No scene classes found in the Manim code")
                return False, "No scene classes found in the Manim code", []
            
            logger.info(f"Found {len(scene_names)} scene classes: {', '.join(scene_names)}")
            
            # Execute Manim for each scene
            output_files = []
            for scene_name in scene_names:
                success, error_msg, output_file = self._run_manim(filename, scene_name)
                
                if not success:
                    return False, error_msg, []
                
                if output_file:
                    output_files.append(output_file)
            
            # If no output files were found in stdout but Manim executed successfully, 
            # look for them in the media directory
            if success and not output_files:
                logger.info("No output files found in stdout, searching media directory")
                found_files = self._find_generated_videos(filename)
                if found_files:
                    logger.info(f"Found {len(found_files)} video files in media directory")
                    output_files.extend(found_files)
            
            return True, "", output_files
            
        except Exception as e:
            logger.error(f"Error executing Manim code: {str(e)}")
            return False, str(e), []
    
    def _extract_scene_classes(self, manim_code):
        """Extract scene class names from the Manim code."""
        scene_classes = []
        
        # Regular expression to find class definitions that inherit from Scene
        pattern = r"class\s+(\w+)\s*\(\s*Scene\s*\)"
        matches = re.finditer(pattern, manim_code)
        
        for match in matches:
            scene_classes.append(match.group(1))
        
        return scene_classes
    
    def _run_manim(self, script_path, scene_name):
        """Run Manim on a specific scene."""
        logger.info(f"Rendering scene {scene_name}")
        
        # Create a base filename for identifying output files
        base_script_name = os.path.basename(script_path).replace('.py', '')
        
        # Determine quality flag
        quality_flag = "-ql" if MANIM_QUALITY == "low_quality" else \
                       "-qm" if MANIM_QUALITY == "medium_quality" else \
                       "-qh" if MANIM_QUALITY == "high_quality" else "-qm"
        
        # Build the command
        cmd = [
            "manim",
            quality_flag,
            script_path,
            scene_name,
            "--media_dir", self.output_dir
        ]
        
        # Execute the command
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Check for errors
            if result.returncode != 0:
                logger.error(f"Manim execution failed with error: {result.stderr}")
                return False, result.stderr, None
            
            # Extract output file path from Manim output
            file_pattern = r"File written to: (.*\.mp4)"
            match = re.search(file_pattern, result.stdout)
            
            if match:
                output_file = match.group(1)
                logger.info(f"Manim successfully rendered {scene_name} to {output_file}")
                return True, "", output_file
            else:
                # Try to find the file in the media directory
                logger.warning(f"Manim execution succeeded but no output file found in stdout")
                
                # Look for partial movie files
                quality_suffix = "480p15" if quality_flag == "-ql" else "720p30" if quality_flag == "-qm" else "1080p60"
                video_dir = os.path.join(self.output_dir, "videos", base_script_name, quality_suffix)
                
                # Check if the directory exists
                if os.path.exists(video_dir):
                    scene_videos = os.path.join(video_dir, scene_name + ".mp4")
                    if os.path.exists(scene_videos):
                        logger.info(f"Found video file: {scene_videos}")
                        return True, "", scene_videos
                
                return True, "", None
                
        except Exception as e:
            logger.error(f"Error running Manim: {str(e)}")
            return False, str(e), None
    
    def _find_generated_videos(self, script_path):
        """Find video files generated by Manim for the given script."""
        base_script_name = os.path.basename(script_path).replace('.py', '')
        
        # Look in various quality directories
        video_files = []
        
        # Look for completed videos
        for quality in ["1080p60", "720p30", "480p15"]:
            pattern = os.path.join(self.output_dir, "videos", base_script_name, quality, "*.mp4")
            files = glob.glob(pattern)
            video_files.extend(files)
        
        # If no complete videos, look for partial movie files
        if not video_files:
            for quality in ["1080p60", "720p30", "480p15"]:
                pattern = os.path.join(self.output_dir, "videos", base_script_name, quality, "partial_movie_files", "*", "*.mp4")
                files = glob.glob(pattern)
                
                # Group by scene folder
                scenes = {}
                for file in files:
                    scene_folder = os.path.basename(os.path.dirname(file))
                    if scene_folder not in scenes:
                        scenes[scene_folder] = []
                    scenes[scene_folder].append(file)
                
                # Take one file from each scene for now (ideally we would merge them)
                for scene_files in scenes.values():
                    if scene_files:
                        video_files.append(scene_files[0])
        
        return video_files
