"""
@Author         : Ailitonia
@Date           : 2025/4/9 15:41:47
@FileName       : embeddings.py
@Project        : omega-miya
@Description    : openai embeddings model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .base import BaseOpenAIModel


class EmbeddingData(BaseOpenAIModel):
    object: str
    embedding: list[float]
    index: int


class Usage(BaseOpenAIModel):
    prompt_tokens: int = -1
    completion_tokens: int = -1
    total_tokens: int = -1


class Embeddings(BaseOpenAIModel):
    object: str
    data: list[EmbeddingData]
    model: str
    usage: Usage


__all__ = [
    'Embeddings',
]
