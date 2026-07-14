from __future__ import annotations

import hashlib
import math
import re


def tokenize(text: str) -> list[str]:
    lowered = text.casefold()
    ascii_tokens = re.findall(r"[a-z][a-z0-9+.#_-]*|\d+", lowered)
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", lowered)
    chinese_tokens: list[str] = []
    for run in chinese_runs:
        if len(run) == 1:
            chinese_tokens.append(run)
        else:
            chinese_tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    return ascii_tokens + chinese_tokens


def hashed_embedding(text: str, dimensions: int = 384) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "little")
        index = value % dimensions
        vector[index] += -1.0 if value & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def lexical_score(query: str, text: str) -> float:
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(tokenize(text))
    overlap = len(query_tokens & text_tokens)
    return overlap / math.sqrt(len(query_tokens) * max(len(text_tokens), 1))
