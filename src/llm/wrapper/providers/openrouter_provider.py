
import os
from typing import List

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from .base import BaseProvider, GenerationResult

class OpenRouterProvider(BaseProvider):
    def __init__(self, temperature: float = 0.1):
        super().__init__(temperature)
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found")
            
        self.llm = ChatOpenAI(
            model="google/gemini-2.0-flash-exp:free",
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
        )

    @property
    def id(self) -> str:
        return "openrouter"

    @property
    def name(self) -> str:
        return "OpenRouter (Gemini Free)"

    def generate(self, messages: List[BaseMessage]) -> GenerationResult:
        return self._track_generation(self.llm.invoke, messages)
