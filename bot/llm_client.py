"""
OpenAI LLM client for task description improvement and translation
"""
import os
from typing import Optional
import openai


class LLMClient:
    """Client for interacting with OpenAI GPT-4 API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key

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
        if not self.api_key:
            return None

        try:
            # Build user prompt based on mode
            if mode == 'translate':
                language_names = {
                    'en': 'English',
                    'tr': 'Turkish',
                    'de': 'German',
                    'fr': 'French',
                    'es': 'Spanish'
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

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )

            improved_text = response.choices[0].message.content.strip()
            return improved_text

        except Exception as e:
            print(f"LLM API error: {e}")
            return None

    def is_available(self) -> bool:
        """Check if LLM API is available"""
        return self.api_key is not None
