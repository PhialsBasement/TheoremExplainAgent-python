import os
import logging
import argparse
import subprocess
import traceback
import json
import tempfile
from collections import OrderedDict

logger = logging.getLogger(__name__)

class VideoAssembler:
    def __init__(self, output_dir="videos"):
        """Initialize the Video Assembler."""
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Initialized VideoAssembler with output directory: {self.output_dir}")

    def get_duration(self, file_path):
        """Get the duration of a media file in seconds."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        try:
            output = subprocess.check_output(cmd, universal_newlines=True).strip()
            return float(output)
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.error(f"Error getting duration for {file_path}: {str(e)}")
            return 0

    def get_video_properties(self, video_path):
        """Get video properties like resolution, fps, etc."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name",
            "-of", "json",
            video_path
        ]
        try:
            output = subprocess.check_output(cmd, universal_newlines=True).strip()
            data = json.loads(output)
            if 'streams' in data and data['streams']:
                stream = data['streams'][0]

                # Parse frame rate which might be in "num/den" format
                fps = stream.get('r_frame_rate', '30/1')
                if '/' in fps:
                    num, den = map(int, fps.split('/'))
                    fps = num / den if den != 0 else 30
                else:
                    fps = float(fps)

                return {
                    'width': stream.get('width', 1280),
                    'height': stream.get('height', 720),
                    'fps': fps,
                    'codec': stream.get('codec_name', 'h264')
                }
        except Exception as e:
            logger.error(f"Error getting video properties for {video_path}: {str(e)}")

        # Return defaults if anything fails
        return {'width': 1280, 'height': 720, 'fps': 30, 'codec': 'h264'}

    def extend_video_duration(self, video_path, target_duration, output_path):
        """
        Extend video duration to match target duration by:
        1. Creating a clean freeze-frame of the last frame with matching properties
        2. Ensuring seamless transition by using the same codec and properties
        """
        video_duration = self.get_duration(video_path)

        if video_duration >= target_duration:
            # No need to extend, just copy
            logger.info(f"Video duration ({video_duration}s) already matches or exceeds target ({target_duration}s)")
            cmd = ["ffmpeg", "-i", video_path, "-c", "copy", "-y", output_path]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_path

        # Calculate how much time to add by freezing the last frame
        freeze_duration = target_duration - video_duration
        logger.info(f"Extending video by {freeze_duration}s by freezing last frame")

        # Get video properties to match in the freeze frame
        properties = self.get_video_properties(video_path)

        # Create a temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract the last frame - use a more robust method than -sseof
            # First get the duration from ffprobe
            duration = self.get_duration(video_path)

            # Use this duration to extract the last frame
            last_frame = os.path.join(temp_dir, "last_frame.png")
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", str(max(0, duration - 0.1)),  # Seek to the last 0.1 seconds
                "-vframes", "1",  # Extract just one frame
                "-y",
                last_frame
            ]

            try:
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                # If that fails, try without seeking
                logger.warning("Failed to extract last frame with seeking, trying simpler method")
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-vframes", "1",  # Just grab the first frame if all else fails
                    "-y",
                    last_frame
                ]
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Create a video from the last frame with matching properties
            freeze_video = os.path.join(temp_dir, "freeze.mp4")
            cmd = [
                "ffmpeg",
                "-loop", "1",
                "-i", last_frame,
                "-t", str(freeze_duration),
                "-vf", f"fps={properties['fps']}",  # Match original FPS
                "-c:v", "libx264",  # Use a high-quality intermediate codec
                "-pix_fmt", "yuv420p",
                "-preset", "medium",
                "-b:v", "5000k",    # Use high bitrate for quality
                "-y",
                freeze_video
            ]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Create a silent audio track if needed
            silent_audio = os.path.join(temp_dir, "silence.mp3")
            cmd = [
                "ffmpeg",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(freeze_duration),
                "-y",
                silent_audio
            ]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Add silent audio to freeze video
            freeze_with_audio = os.path.join(temp_dir, "freeze_with_audio.mp4")
            cmd = [
                "ffmpeg",
                "-i", freeze_video,
                "-i", silent_audio,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                "-y",
                freeze_with_audio
            ]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Try simplest and most reliable concat approach
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as f:
                f.write(f"file '{os.path.abspath(video_path)}'\n")
                f.write(f"file '{os.path.abspath(freeze_with_audio)}'\n")

            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-y",
                output_path
            ]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return output_path

    def assemble_video(self, video_files, audio_files=None, output_filename=None):
        """
        Assemble multiple video clips into a single video with synchronized audio.

        Args:
            video_files (list): List of paths to video files to be assembled in order.
            audio_files (dict): Dictionary mapping scene indexes to audio file paths.
            output_filename (str, optional): Path to save the final output video.

        Returns:
            str: Path to the assembled video file if successful, None otherwise.
        """
        try:
            if not video_files:
                logger.error("No video files provided.")
                return None

            logger.info(f"Using provided video files: {len(video_files)} files")
            logger.info(f"Using provided audio files: {len(audio_files) if audio_files else 0} files")

            if output_filename is None:
                output_filename = os.path.join(self.output_dir, "theorem_explanation.mp4")

            logger.info(f"Assembling {len(video_files)} video clips")

            # Create a temporary directory for intermediate files
            temp_dir = os.path.join(self.output_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)

            # Process each video segment with its corresponding audio
            video_segments_with_audio = []

            for i, video_file in enumerate(video_files):
                if audio_files and i in audio_files and os.path.exists(audio_files[i]):
                    # Get durations
                    audio_file = audio_files[i]
                    audio_duration = self.get_duration(audio_file)
                    video_duration = self.get_duration(video_file)

                    logger.info(f"Segment {i}: Video duration={video_duration}s, Audio duration={audio_duration}s")

                    # 1. Make sure the video is at least as long as the audio
                    extended_video_path = os.path.join(temp_dir, f"extended_video_{i}.mp4")
                    if video_duration < audio_duration:
                        # Add a buffer to ensure audio fits completely
                        target_duration = audio_duration + 0.5  # Add half a second buffer
                        logger.info(f"Video {i} is shorter than audio. Extending to {target_duration}s")
                        self.extend_video_duration(video_file, target_duration, extended_video_path)
                        video_to_use = extended_video_path
                    else:
                        logger.info(f"Video {i} is already longer than audio. Using as is.")
                        video_to_use = video_file

                    # 2. Add audio to the (possibly extended) video
                    segment_output = os.path.join(temp_dir, f"segment_{i}_with_audio.mp4")
                    logger.info(f"Adding audio to video segment {i}")

                    cmd = [
                        "ffmpeg",
                        "-i", video_to_use,
                        "-i", audio_file,
                        "-map", "0:v:0",        # Video from first input
                        "-map", "1:a:0",        # Audio from second input
                        "-c:v", "libx264",      # Re-encode for consistency
                        "-crf", "18",           # High quality setting
                        "-preset", "medium",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-y",                   # Overwrite output if exists
                        segment_output
                    ]

                    logger.info(f"Running ffmpeg command for segment {i}")
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    # Verify the new segment has the correct duration
                    new_duration = self.get_duration(segment_output)
                    logger.info(f"Segment {i} with audio has duration: {new_duration}s")

                    video_segments_with_audio.append(segment_output)
                else:
                    # No audio for this segment, just copy the video
                    logger.info(f"No audio file for segment {i}, using original video")
                    segment_output = os.path.join(temp_dir, f"segment_{i}_no_audio.mp4")

                    # Ensure consistent encoding across all segments
                    cmd = [
                        "ffmpeg",
                        "-i", video_file,
                        "-c:v", "libx264",
                        "-crf", "18",
                        "-preset", "medium",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-y",
                        segment_output
                    ]
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    video_segments_with_audio.append(segment_output)

            # Now combine all segments into final video
            file_list_path = os.path.join(temp_dir, "ffmpeg_file_list.txt")
            with open(file_list_path, "w") as f:
                for segment in video_segments_with_audio:
                    f.write(f"file '{os.path.abspath(segment)}'\n")

            logger.info(f"Concatenating {len(video_segments_with_audio)} video segments")

            # Use the concat demuxer with re-encoding for better compatibility
            cmd_concat = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", file_list_path,
                "-c:v", "libx264",       # Re-encode for consistency
                "-crf", "18",            # High quality
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "192k",
                "-y",                    # Overwrite output if exists
                output_filename
            ]

            logger.info(f"Running final concatenation command")
            subprocess.check_call(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Clean up temporary files
            for segment in video_segments_with_audio:
                if segment.startswith(temp_dir) and os.path.exists(segment):
                    try:
                        os.remove(segment)
                    except OSError as e:
                        logger.warning(f"Could not remove temporary file {segment}: {str(e)}")

            if os.path.exists(file_list_path):
                try:
                    os.remove(file_list_path)
                except OSError as e:
                    logger.warning(f"Could not remove file list {file_list_path}: {str(e)}")

            # Try to remove temp directory
            try:
                os.rmdir(temp_dir)
            except OSError:
                logger.warning(f"Could not remove temporary directory: {temp_dir}")

            logger.info(f"Video assembled and saved to {output_filename}")
            return output_filename

        except Exception as e:
            logger.error(f"Error assembling video: {str(e)}\n{traceback.format_exc()}")
            return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble video using ffmpeg with provided file lists")
    parser.add_argument("--videos", type=str, required=True,
                        help="Path to a text file containing video file paths (one per line)")
    parser.add_argument("--audio", type=str,
                        help="Path to a JSON file mapping indices to audio file paths")
    parser.add_argument("--output", type=str, default=None,
                        help="Output filename (optional)")
    parser.add_argument("--output_dir", type=str, default="final",
                        help="Output directory")

    args = parser.parse_args()

    # Read video file paths from the provided text file.
    with open(args.videos, "r") as vf:
        video_files = [line.strip() for line in vf if line.strip()]

    # If an audio file is provided, read the JSON mapping.
    audio_files = None
    if args.audio:
        if args.audio.endswith('.json'):
            with open(args.audio, 'r') as af:
                audio_files = json.load(af)
        else:
            # Backward compatibility: single audio file
            audio_files = {0: args.audio}

    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    assembler = VideoAssembler(output_dir=args.output_dir)
    result = assembler.assemble_video(video_files=video_files, audio_files=audio_files, output_filename=args.output)
    if result:
        print(f"Video assembled successfully: {result}")
    else:
        print("Failed to assemble video.")
