import re


def split_markdown(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
    sections = re.split(r"(?=^#{1,4} )", text, flags=re.M)
    chunks: list[str] = []
    buffer = ""
    for section in sections:
        if not section.strip():
            continue
        if len(buffer) + len(section) <= max_chars:
            buffer += section
        else:
            if buffer:
                chunks.append(buffer)
            buffer = section
    if buffer:
        chunks.append(buffer)

    merged: list[str] = []
    for index, chunk in enumerate(chunks):
        if index > 0:
            chunk = chunks[index - 1][-overlap:] + chunk
        merged.append(chunk)
    return merged or [text]
