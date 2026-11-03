"""Extrator para arquivos PDF, usando pdfplumber (texto por página)."""

import pdfplumber

from .base import BaseExtractor


class PdfExtractor(BaseExtractor):
    supported_extensions = ("pdf",)

    def extract_text(self, file_path: str) -> str:
        pages_text = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # extract_text() devolve None em páginas sem texto
                # selecionável (ex.: página só com imagem/escaneada).
                pages_text.append(page.extract_text() or "")
        return "\n".join(pages_text)
