# Utilidad para contar tokens de forma aproximada.
# Laura Álvarez Zamora - 19/11/2026

import tiktoken


# Convierte un texto en tokens con la codificación cl100k_base (aproximado: cada modelo usa su propio tokenizador).
def tokenize_text(text: str) -> list[int]:
    encoding = tiktoken.get_encoding("cl100k_base")
    return encoding.encode(text)
