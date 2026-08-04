"""近似 Token 计数。"""

import tiktoken


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """使用 tiktoken 统计文本 Token 数。"""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))
