import os
import logging
from gtts import gTTS

logger = logging.getLogger(__name__)

class TTSHandler:
    def __init__(self, output_dir="audio"):
        """Initialize the Text-to-Speech handler."""
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Initialized TTSHandler with output directory: {self.output_dir}")
    
    def generate_audio(self, text, filename=None, lang="en"):
        """Generate audio from text using TTS."""
        try:
            if filename is None:
                # Create a temporary filename
                temp_filename = f"narration_{hash(text) % 10000:04d}.mp3"
                filename = os.path.join(self.output_dir, temp_filename)
            
            logger.info(f"Generating audio for text ({len(text.split())} words)")
            
            # Convert text to speech
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(filename)
            
            logger.info(f"Audio saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            return None
    
    def generate_scene_audio(self, scene_plan):
        """Generate audio for each scene in the plan."""
        audio_files = {}
        
        for i, scene in enumerate(scene_plan):
            narration = scene.get("narration", "")
            
            if narration:
                # Clean narration text (remove quotes, etc.)
                narration = narration.strip('"\'')
                
                # Generate scene-specific filename
                filename = os.path.join(self.output_dir, f"scene_{i+1:02d}.mp3")
                
                # Generate the audio
                audio_file = self.generate_audio(narration, filename)
                
                if audio_file:
                    audio_files[i] = audio_file
            
        logger.info(f"Generated {len(audio_files)} audio files for {len(scene_plan)} scenes")
        return audio_files
