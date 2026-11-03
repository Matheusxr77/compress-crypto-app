"""
registry.py - Ponto único de acesso aos extractors.

Mapeia extensão de arquivo -> instância de BaseExtractor, para que o
pipeline (e futuramente as rotas) não precisem saber qual classe usar
para cada tipo de arquivo.
"""

import os

from .docx_extractor import DocxExtractor
from .pdf_extractor import PdfExtractor
from .txt_extractor import TxtExtractor

_EXTRACTORS = [TxtExtractor(), PdfExtractor(), DocxExtractor()]

_BY_EXTENSION = {
    ext: extractor for extractor in _EXTRACTORS for ext in extractor.supported_extensions
}


def get_extractor(filename_or_path: str):
    """Devolve a instância de BaseExtractor adequada para o arquivo,
    com base na sua extensão. Lança ValueError se não houver suporte."""
    _, ext = os.path.splitext(filename_or_path)
    ext = ext.lstrip(".").lower()
    extractor = _BY_EXTENSION.get(ext)
    if extractor is None:
        raise ValueError(f"Extensão não suportada: .{ext}")
    return extractor


def extract_text(file_path: str) -> str:
    """Atalho: lê file_path e retorna o texto extraído, escolhendo o
    extractor automaticamente pela extensão."""
    extractor = get_extractor(file_path)
    return extractor.extract_text(file_path)
