
import os
from typing import List

from langchain_core.messages import BaseMessage
from langchain_groq import ChatGroq

from src.shared import logger
from .base import BaseProvider, GenerationResult

class GroqProvider(BaseProvider):
    def __init__(self, temperature: float = 0.1):
        super().__init__(temperature)
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")
            
        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=api_key,
            temperature=temperature,
        )

    @property
    def id(self) -> str:
        return "groq"

    @property
    def name(self) -> str:
        return "Groq (Llama 3.1 8B Instant)"

    def generate(self, messages: List[BaseMessage]) -> GenerationResult:
        return self._track_generation(self.llm.invoke, messages)
