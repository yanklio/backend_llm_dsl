
import os
from typing import List

from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base import BaseProvider, GenerationResult

class GeminiProvider(BaseProvider):
    def __init__(self, temperature: float = 0.1):
        super().__init__(temperature)
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY not found")
            
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", 
            temperature=temperature
        )

    @property
    def id(self) -> str:
        return "gemini"

    @property
    def name(self) -> str:
        return "Google Gemini"

    def generate(self, messages: List[BaseMessage]) -> GenerationResult:
        return self._track_generation(self.llm.invoke, messages)
