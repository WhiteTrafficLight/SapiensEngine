import os
import logging
from gtts import gTTS
from typing import Dict, List, Any
import uuid
import tempfile
from io import BytesIO
from pydub import AudioSegment
import time

logger = logging.getLogger(__name__)

class AudioGenerator:
    """
    Converts dialogue text into speech using text-to-speech APIs.
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize the audio generator.
        
        Args:
            output_dir: Directory to save generated audio files
        """
        if output_dir:
            self.output_dir = output_dir
        else:
            # Create a default directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.output_dir = os.path.join(base_dir, 'generated_audio')
            
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Initializing AudioGenerator with output directory: {self.output_dir}")
        
        # Define voice profiles for different speakers
        # For gTTS, we'll use different languages/accents as a simple way to differentiate voices
        self.voice_profiles = {
            "default": {"lang": "en", "tld": "com"},  # US English
            "socrates": {"lang": "en", "tld": "co.uk"},  # UK English
            "plato": {"lang": "en", "tld": "com.au"},  # Australian English
            "aristotle": {"lang": "en", "tld": "ie"},  # Irish English
            "kant": {"lang": "en", "tld": "ca"},  # Canadian English
            "nietzsche": {"lang": "en", "tld": "co.za"},  # South African English
            "user": {"lang": "en", "tld": "co.in"}  # Indian English
        }
    
    def generate_dialogue_audio(self, 
                               dialogue_exchanges: List[Dict[str, str]],
                               topic: str) -> Dict[str, Any]:
        """
        Generate audio files for each exchange in the dialogue and combine them into a single file.
        
        Args:
            dialogue_exchanges: List of dialogue exchanges (speaker and content)
            topic: Topic of the dialogue
            
        Returns:
            Dictionary with paths to generated audio files
        """
        logger.info(f"Generating audio for dialogue with topic: {topic}")
        
        # Create a unique identifier for this dialogue
        safe_topic = "".join(c if c.isalnum() else "_" for c in topic)
        dialogue_id = str(uuid.uuid4())[:8]
        
        # Make a directory for this dialogue
        dialogue_dir = os.path.join(self.output_dir, f"{safe_topic}_{dialogue_id}")
        os.makedirs(dialogue_dir, exist_ok=True)
        
        # Generate individual audio segments
        audio_segments = []
        individual_files = []
        
        for i, exchange in enumerate(dialogue_exchanges):
            speaker = exchange.get("speaker", "Unknown")
            content = exchange.get("content", "")
            
            if not content:
                continue
                
            # Determine voice profile for this speaker
            voice_profile = self._get_voice_profile(speaker)
            
            # Generate audio for this exchange
            audio_path = self._generate_single_audio(
                text=content,
                speaker=speaker,
                output_dir=dialogue_dir,
                index=i,
                voice_profile=voice_profile
            )
            
            if audio_path:
                # Load the audio segment
                audio_segment = AudioSegment.from_mp3(audio_path)
                
                # Add a pause between speakers (1 second)
                if audio_segments:
                    pause = AudioSegment.silent(duration=1000)
                    audio_segments.append(pause)
                
                # Add speaker announcement
                speaker_announcement = self._generate_speaker_announcement(speaker, dialogue_dir)
                if speaker_announcement:
                    audio_segments.append(AudioSegment.from_mp3(speaker_announcement))
                    # Add a short pause (500ms)
                    audio_segments.append(AudioSegment.silent(duration=500))
                
                # Add the speech
                audio_segments.append(audio_segment)
                
                individual_files.append({
                    "speaker": speaker,
                    "content": content,
                    "audio_path": audio_path
                })
        
        # Combine all audio segments into one file
        if audio_segments:
            combined_audio = audio_segments[0]
            for segment in audio_segments[1:]:
                combined_audio += segment
                
            # Save the combined audio
            combined_path = os.path.join(dialogue_dir, f"complete_dialogue.mp3")
            combined_audio.export(combined_path, format="mp3")
            logger.info(f"Generated combined audio file: {combined_path}")
        else:
            combined_path = None
            logger.warning("No audio segments to combine")
        
        result = {
            "topic": topic,
            "audio_files": individual_files,
            "combined_audio_path": combined_path,
            "dialogue_dir": dialogue_dir
        }
        
        logger.info(f"Generated {len(individual_files)} individual audio files and 1 combined file")
        return result
    
    def _generate_speaker_announcement(self, speaker: str, output_dir: str) -> str:
        """Generate a brief announcement of who is speaking"""
        try:
            # Create a filename for the announcement
            safe_speaker = "".join(c if c.isalnum() else "_" for c in speaker)
            filename = f"announce_{safe_speaker}.mp3"
            output_path = os.path.join(output_dir, filename)
            
            # Check if this announcement already exists
            if os.path.exists(output_path):
                return output_path
                
            # Generate the announcement
            announcement_text = f"{speaker} says:"
            tts = gTTS(text=announcement_text, lang='en', slow=False)
            tts.save(output_path)
            
            return output_path
        except Exception as e:
            logger.error(f"Error generating speaker announcement: {str(e)}")
            return None
    
    def _generate_single_audio(self, 
                              text: str, 
                              speaker: str, 
                              output_dir: str, 
                              index: int,
                              voice_profile: Dict[str, Any]) -> str:
        """
        Generate audio for a single dialogue exchange.
        
        Args:
            text: Text to convert to speech
            speaker: Name of the speaker
            output_dir: Directory to save the audio file
            index: Index of this exchange in the dialogue
            voice_profile: Voice configuration for this speaker
            
        Returns:
            Path to the generated audio file
        """
        try:
            # Create a safe filename from the speaker name
            safe_speaker = "".join(c if c.isalnum() else "_" for c in speaker)
            filename = f"{index:02d}_{safe_speaker}.mp3"
            output_path = os.path.join(output_dir, filename)
            
            # Use gTTS to convert text to speech with the specified voice profile
            tts = gTTS(text=text, lang=voice_profile["lang"], tld=voice_profile["tld"], slow=False)
            tts.save(output_path)
            
            logger.info(f"Generated audio file: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating audio for {speaker}: {str(e)}")
            return None
    
    def _get_voice_profile(self, speaker: str) -> Dict[str, Any]:
        """Get the appropriate voice profile for the speaker"""
        # Convert speaker name to lowercase and remove spaces
        key = speaker.lower().replace(" ", "_")
        
        # Try to match with known profiles
        for profile_key in self.voice_profiles:
            if profile_key in key:
                return self.voice_profiles[profile_key]
        
        # If no match, use a deterministic approach to select a voice profile
        # This ensures the same speaker always gets the same voice
        available_profiles = list(self.voice_profiles.values())
        profile_index = hash(speaker) % len(available_profiles)
        return available_profiles[profile_index] 
 