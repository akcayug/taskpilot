"""
OpenAI Whisper client for speech-to-text transcription
"""
import os
from typing import Optional
from openai import OpenAI


class SpeechClient:
    """Client for transcribing audio using OpenAI Whisper API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    async def transcribe_voice_message(self, file_path: str) -> Optional[str]:
        """
        Transcribe a voice message audio file

        Args:
            file_path: Path to the audio file

        Returns:
            Transcribed text or None on error
        """
        if not self.client:
            return None

        try:
            with open(file_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=None  # Auto-detect language
                )

            transcription = response.text.strip() if response.text else None
            return transcription if transcription else None

        except Exception as e:
            print(f"Speech API error: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Speech API is available"""
        return self.client is not None
