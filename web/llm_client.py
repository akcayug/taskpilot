"""
OpenAI LLM client for web task form AI assistance
"""
import os
from typing import Optional
import openai


class WebLLMClient:
    """Client for interacting with OpenAI GPT-4 API for web forms"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key

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
                    f"Translate the following text to {target_lang_name}. "
                    f"Keep it clear and concise:\n\n{text}"
                )
            else:  # mode == 'fix'
                user_prompt = (
                    f"Improve the following text. "
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
                max_tokens=300
            )

            improved_text = response.choices[0].message.content.strip()

            return {
                'success': True,
                'text': improved_text
            }

        except openai.error.AuthenticationError:
            return {
                'success': False,
                'error': 'Invalid OpenAI API key'
            }
        except openai.error.RateLimitError:
            return {
                'success': False,
                'error': 'Rate limit exceeded. Please try again later.'
            }
        except openai.error.APIError as e:
            return {
                'success': False,
                'error': f'OpenAI API error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }

    def is_available(self) -> bool:
        """Check if LLM API is available"""
        return self.api_key is not None
