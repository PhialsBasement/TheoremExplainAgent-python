import os
import subprocess
import re

# Path to the output directory
output_dir = "/home/phiality/TheoremPaperImplement/examples/outputs/Pythagorean_Theorem"

# Find all rendered videos
videos_dir = os.path.join(output_dir, "media", "videos")
scene_videos = []

print("Finding all rendered videos...")

# Find videos in the media/videos directory
if os.path.exists(videos_dir):
    for scene_dir in os.listdir(videos_dir):
        scene_dir_path = os.path.join(videos_dir, scene_dir)
        if os.path.isdir(scene_dir_path):
            for file in os.listdir(scene_dir_path):
                if file.endswith(".mp4"):
                    # Extract scene number from the directory name or file name
                    scene_match = re.search(r"Scene(\d+)", scene_dir)
                    if scene_match:
                        scene_num = int(scene_match.group(1))
                        scene_videos.append((scene_num, os.path.join(scene_dir_path, file)))
                    else:
                        # Try to find the scene number in the file name as fallback
                        scene_match = re.search(r"Scene(\d+)", file)
                        if scene_match:
                            scene_num = int(scene_match.group(1))
                            scene_videos.append((scene_num, os.path.join(scene_dir_path, file)))

# Sort videos by scene number
scene_videos.sort()
video_files = [video_path for _, video_path in scene_videos]

if not video_files:
    print("No video files found to combine")
    exit(1)

print(f"Found {len(video_files)} videos to combine")
for i, video in enumerate(video_files):
    print(f"  {i+1}. {os.path.basename(video)}")

# Create list file for ffmpeg
list_file = os.path.join(output_dir, "video_list.txt")
with open(list_file, "w") as f:
    for video_file in video_files:
        f.write(f"file '{video_file}'\n")

# Combine videos using ffmpeg
output_video = os.path.join(output_dir, "final", "combined_theorem_video.mp4")
os.makedirs(os.path.dirname(output_video), exist_ok=True)

cmd = [
    "ffmpeg",
    "-f", "concat",
    "-safe", "0",
    "-i", list_file,
    "-c", "copy",
    output_video
]

print("\nCombining videos...")
try:
    result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"Successfully combined videos into {output_video}")
except subprocess.CalledProcessError as e:
    print(f"Error combining videos: {e.stderr.decode()}")
    exit(1)

print("All done! Combined all scenes successfully.")
