"""Extrator para arquivos de texto puro (.txt)."""

from .base import BaseExtractor


class TxtExtractor(BaseExtractor):
    supported_extensions = ("txt",)

    def extract_text(self, file_path: str) -> str:
        # errors="replace" evita que um arquivo com encoding inesperado
        # derrube o pipeline inteiro; caracteres inválidos viram "�".
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
