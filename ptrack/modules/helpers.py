def find_substring(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker) + len(start_marker)
    return text[start:text.index(end_marker, start)]



