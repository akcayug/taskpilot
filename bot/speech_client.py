"""
OpenAI Whisper client for speech-to-text transcription
"""
import os
from typing import Optional
import openai
import tempfile


class SpeechClient:
    """Client for transcribing audio using OpenAI Whisper API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key

    async def transcribe_voice_message(self, file_path: str) -> Optional[str]:
        """
        Transcribe a voice message audio file

        Args:
            file_path: Path to the audio file

        Returns:
            Transcribed text or None on error
        """
        if not self.api_key:
            return None

        try:
            with open(file_path, 'rb') as audio_file:
                response = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file,
                    language=None  # Auto-detect language
                )

            transcription = response.get('text', '').strip()
            return transcription if transcription else None

        except Exception as e:
            print(f"Speech API error: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Speech API is available"""
        return self.api_key is not None
