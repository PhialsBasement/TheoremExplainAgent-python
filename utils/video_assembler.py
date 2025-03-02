import os
import logging
import glob
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
import traceback

logger = logging.getLogger(__name__)

class VideoAssembler:
    def __init__(self, output_dir="videos"):
        """Initialize the Video Assembler."""
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Initialized VideoAssembler with output directory: {self.output_dir}")
    
    def assemble_video(self, video_files, audio_files=None, output_filename=None):
        """Assemble multiple video clips into a single video, optionally with audio."""
        try:
            if not video_files:
                # If no files are provided, search for video files in the media directory
                logger.info("No video files provided, searching for video files in media directory")
                media_dir = os.path.dirname(self.output_dir)  # Assuming media_dir is parent of output_dir
                if "final" in self.output_dir:
                    media_dir = os.path.dirname(self.output_dir)
                    media_dir = os.path.join(media_dir, "media")
                
                # Search for video files
                video_files = []
                for ext in ['.mp4', '.avi', '.mov', '.mkv']:
                    found_files = glob.glob(os.path.join(media_dir, "**", f"*{ext}"), recursive=True)
                    # Skip temporary files created by moviepy
                    video_files.extend([f for f in found_files if not os.path.basename(f).startswith("TEMP")])
                
                # Sort by creation time - latest first
                video_files.sort(key=lambda x: os.path.getctime(x), reverse=True)
                
                if not video_files:
                    logger.error("No video files found in media directory")
                    return None
                else:
                    # Take only the most recent files to avoid older versions
                    seen_basenames = set()
                    filtered_files = []
                    for file in video_files:
                        basename = os.path.basename(file).split('.')[0]
                        if basename not in seen_basenames:
                            seen_basenames.add(basename)
                            filtered_files.append(file)
                    
                    video_files = filtered_files[:5]  # Limit to 5 most recent files
                
                logger.info(f"Found {len(video_files)} video files: {video_files}")
            
            if output_filename is None:
                # Create a default output filename
                output_filename = os.path.join(self.output_dir, "theorem_explanation.mp4")
            
            logger.info(f"Assembling {len(video_files)} video clips")
            
            # Load video clips
            video_clips = []
            for video_file in video_files:
                try:
                    clip = VideoFileClip(video_file)
                    if clip.duration > 0:  # Only add valid clips
                        video_clips.append(clip)
                    else:
                        logger.warning(f"Skipping video file with zero duration: {video_file}")
                        clip.close()
                except Exception as e:
                    logger.error(f"Error loading video file {video_file}: {str(e)}")
                    continue
            
            if not video_clips:
                logger.error("No valid video clips to assemble")
                return None
            
            # Concatenate video clips
            logger.info(f"Concatenating {len(video_clips)} video clips")
            try:
                final_clip = concatenate_videoclips(video_clips, method="compose")
            except Exception as e:
                logger.error(f"Error concatenating clips: {str(e)}")
                # Try composing just one clip for demonstration
                if len(video_clips) > 0:
                    final_clip = video_clips[0]
                else:
                    for clip in video_clips:
                        clip.close()
                    return None
            
            # Add audio if provided
            if audio_files and isinstance(audio_files, dict) and len(audio_files) > 0:
                try:
                    logger.info(f"Adding {len(audio_files)} audio tracks")
                    # Create a list for audio clips
                    audio_clips = []
                    
                    # Get first scene audio
                    if 0 in audio_files and os.path.exists(audio_files[0]):
                        try:
                            main_audio = AudioFileClip(audio_files[0])
                            audio_clips.append(main_audio)
                        except Exception as e:
                            logger.error(f"Error loading audio file {audio_files[0]}: {str(e)}")
                    
                    if audio_clips:
                        # Set the audio
                        final_clip = final_clip.set_audio(CompositeAudioClip(audio_clips))
                except Exception as e:
                    logger.error(f"Error adding audio: {str(e)}\n{traceback.format_exc()}")
            
            # Write the final video to file
            logger.info(f"Writing video to {output_filename}")
            final_clip.write_videofile(
                output_filename, 
                codec="libx264", 
                audio_codec="aac" if hasattr(final_clip, 'audio') and final_clip.audio is not None else None,
                verbose=False,
                logger=None
            )
            
            # Close all clips to free up resources
            final_clip.close()
            for clip in video_clips:
                if hasattr(clip, 'close'):
                    clip.close()
            
            logger.info(f"Video assembled and saved to {output_filename}")
            return output_filename
            
        except Exception as e:
            logger.error(f"Error assembling video: {str(e)}\n{traceback.format_exc()}")
            return None
