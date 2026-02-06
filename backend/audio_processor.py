"""
Audio Processing Module
Handles various audio processing operations using pydub
"""

from pydub import AudioSegment
from pydub.effects import normalize
import os


class AudioProcessor:
    """Class to handle audio processing operations"""
    
    def __init__(self):
        """Initialize AudioProcessor"""
        pass
    
    def get_audio_info(self, filepath):
        """
        Get information about an audio file
        
        Args:
            filepath: Path to the audio file
            
        Returns:
            Dictionary containing audio information
        """
        audio = AudioSegment.from_file(filepath)
        
        return {
            'duration': len(audio) / 1000.0,  # Duration in seconds
            'channels': audio.channels,
            'sample_width': audio.sample_width,
            'frame_rate': audio.frame_rate,
            'frame_width': audio.frame_width,
            'max_possible_amplitude': audio.max_possible_amplitude,
            'file_size': os.path.getsize(filepath)
        }
    
    def normalize_audio(self, input_path, output_path):
        """
        Normalize audio volume
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save normalized audio
        """
        audio = AudioSegment.from_file(input_path)
        normalized_audio = normalize(audio)
        normalized_audio.export(output_path, format=self._get_format_from_path(output_path))
    
    def trim_audio(self, input_path, output_path, start_time, end_time):
        """
        Trim audio to specified time range
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save trimmed audio
            start_time: Start time in seconds
            end_time: End time in seconds
        """
        audio = AudioSegment.from_file(input_path)
        
        # Convert seconds to milliseconds
        start_ms = start_time * 1000
        end_ms = end_time * 1000
        
        # Trim audio
        trimmed_audio = audio[start_ms:end_ms]
        trimmed_audio.export(output_path, format=self._get_format_from_path(output_path))
    
    def change_speed(self, input_path, output_path, speed_factor=1.0):
        """
        Change audio playback speed
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save modified audio
            speed_factor: Speed multiplier (e.g., 2.0 for 2x speed)
        """
        audio = AudioSegment.from_file(input_path)
        
        # Change frame rate to modify speed
        new_frame_rate = int(audio.frame_rate * speed_factor)
        modified_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
        modified_audio = modified_audio.set_frame_rate(audio.frame_rate)
        
        modified_audio.export(output_path, format=self._get_format_from_path(output_path))
    
    def adjust_volume(self, input_path, output_path, volume_change_db):
        """
        Adjust audio volume by specified decibels
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save modified audio
            volume_change_db: Volume change in decibels (positive to increase, negative to decrease)
        """
        audio = AudioSegment.from_file(input_path)
        adjusted_audio = audio + volume_change_db
        adjusted_audio.export(output_path, format=self._get_format_from_path(output_path))
    
    def _get_format_from_path(self, filepath):
        """
        Extract file format from filepath
        
        Args:
            filepath: Path to file
            
        Returns:
            File format string
        """
        _, ext = os.path.splitext(filepath)
        return ext[1:].lower() if ext else 'wav'
