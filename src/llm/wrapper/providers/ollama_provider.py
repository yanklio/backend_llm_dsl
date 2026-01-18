
import requests
from typing import List

from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama

from .base import BaseProvider, GenerationResult

class OllamaProvider(BaseProvider):
    def __init__(self, temperature: float = 0.1):
        super().__init__(temperature)
        
        # Check connection eagerly
        try:
            requests.get("http://localhost:11434", timeout=1)
        except Exception:
            raise ConnectionError("Ollama is not running on localhost:11434")

        self.llm = ChatOllama(
            model="llama3.1", 
            temperature=temperature
        )

    @property
    def id(self) -> str:
        return "ollama"

    @property
    def name(self) -> str:
        return "Ollama (Local)"

    def generate(self, messages: List[BaseMessage]) -> GenerationResult:
        return self._track_generation(self.llm.invoke, messages)
