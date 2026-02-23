"""
OpenAI LLM client for task description improvement and translation
"""
import os
from typing import Optional
from openai import OpenAI


class LLMClient:
    """Client for interacting with OpenAI GPT-4 API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def improve_task_text(
        self,
        text: str,
        system_prompt: str,
        mode: str = 'fix',
        target_language: str = 'en'
    ) -> Optional[str]:
        """
        Improve task text using LLM

        Args:
            text: Raw task text from voice or user input
            system_prompt: Custom system prompt from tenant settings
            mode: 'fix' or 'translate'
            target_language: Target language code (en, tr, de, fr, es)

        Returns:
            Improved task text or None on error
        """
        import logging
        logger = logging.getLogger(__name__)

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set")
            return None

        try:
            logger.info(f"Calling OpenAI API with mode={mode}, lang={target_language}")
            # Build user prompt based on mode
            if mode == 'translate':
                language_names = {
                    'en': 'English',
                    'tr': 'Turkish',
                    'de': 'German',
                    'fr': 'French',
                    'es': 'Spanish',
                    'ru': 'Russian'
                }
                target_lang_name = language_names.get(target_language, 'English')
                user_prompt = (
                    f"Translate the following task description to {target_lang_name}. "
                    f"Keep it clear and concise:\n\n{text}"
                )
            else:  # mode == 'fix'
                user_prompt = (
                    f"Improve the following task description. "
                    f"Fix grammar, make it clear and professional:\n\n{text}"
                )

            # Call OpenAI API (v1.x format)
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )

            improved_text = response.choices[0].message.content.strip()
            logger.info(f"OpenAI API success: {improved_text[:100]}...")
            return improved_text

        except Exception as e:
            logger.exception(f"LLM API error: {e}")
            return None

    def is_available(self) -> bool:
        """Check if LLM API is available"""
        return self.client is not None
