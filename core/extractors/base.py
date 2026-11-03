"""
Interface padrão para extração de conteúdo dos arquivos de entrada.

Cada tipo suportado (.txt, .pdf, .docx) terá sua própria subclasse de
BaseExtractor (TxtExtractor, PdfExtractor, DocxExtractor), devolvendo
sempre texto puro — a entrada da etapa seguinte do pipeline (localização
de palavras-chave e criptografia).

Implementação das subclasses: próxima etapa.
"""

from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """Classe base que todo leitor de arquivo deve implementar."""

    #: extensões (sem o ponto) que esta subclasse sabe processar
    supported_extensions: tuple = ()

    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """Lê o arquivo em file_path e retorna seu conteúdo textual."""
        raise NotImplementedError
