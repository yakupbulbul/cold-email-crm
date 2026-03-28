from openai import OpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class OpenAIProvider:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def execute_prompt(self, system_prompt: str, user_prompt: str) -> str:
        if not self.client:
            return "AI features are disabled because no OpenAI API Key was provided."
            
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=250,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            return f"Error analyzing thread: {e}"
