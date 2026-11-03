"""Extrator para documentos Word (.docx), usando python-docx."""

import docx

from .base import BaseExtractor


class DocxExtractor(BaseExtractor):
    supported_extensions = ("docx",)

    def extract_text(self, file_path: str) -> str:
        document = docx.Document(file_path)
        paragraphs = [p.text for p in document.paragraphs]
        return "\n".join(paragraphs)
