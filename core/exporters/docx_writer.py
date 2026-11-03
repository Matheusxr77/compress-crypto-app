"""Exportação do texto reconstruído para DOCX."""

import os

from docx import Document


def write_text_docx(path: str, text: str) -> None:
    document = Document()
    for line in text.splitlines() or [""]:
        document.add_paragraph(line)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    document.save(path)
