"""
OpenAI LLM client for web task form AI assistance
"""
import os
from typing import Optional
from openai import OpenAI


class WebLLMClient:
    """Client for interacting with OpenAI GPT-4 API for web forms"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def improve_text(
        self,
        text: str,
        system_prompt: str,
        mode: str = 'fix',
        target_language: str = 'en'
    ) -> dict:
        """
        Improve text using LLM

        Args:
            text: Original text to improve
            system_prompt: Custom system prompt from tenant settings
            mode: 'fix' or 'translate'
            target_language: Target language code (en, tr, de, fr, es)

        Returns:
            Dict with 'success', 'text', and optional 'error' keys
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'OpenAI API key not configured'
            }

        if not text or not text.strip():
            return {
                'success': False,
                'error': 'Text is empty'
            }

        try:
            # Use system prompt directly without additional instructions
            # The system prompt should contain all necessary instructions
            # for how to handle the text (translate, fix, etc.)

            # Call OpenAI API (v1.x format)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}  # Just the raw text
                ],
                temperature=0.7,
                max_tokens=300
            )

            improved_text = response.choices[0].message.content.strip()

            return {
                'success': True,
                'text': improved_text
            }

        except Exception as e:
            error_msg = str(e)
            # Check for common error types
            if 'authentication' in error_msg.lower() or 'api key' in error_msg.lower():
                return {
                    'success': False,
                    'error': 'Invalid OpenAI API key'
                }
            elif 'rate limit' in error_msg.lower():
                return {
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.'
                }
            else:
                return {
                    'success': False,
                    'error': f'AI service error: {error_msg}'
                }

    def is_available(self) -> bool:
        """Check if LLM API is available"""
        return self.client is not None
