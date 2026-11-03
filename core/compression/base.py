"""
Interface padrão para todos os algoritmos de compressão sem perdas.

Cada um dos 10 métodos (Huffman, Arithmetic, BWT, Golomb, LZ77, LZMA,
LZW, PAQ, PPM, RLE) será implementado como uma subclasse de
BaseCompressor em seu próprio módulo, permitindo que o pipeline, a opção
"Todos" (execução concorrente) e o dashboard de métricas chamem qualquer
algoritmo de forma intercambiável, sem conhecer sua implementação interna.

Implementação das subclasses e do registry (nome -> classe): próxima etapa.
"""

from abc import ABC, abstractmethod


class BaseCompressor(ABC):
    """Classe base que todo algoritmo de compressão deve implementar."""

    #: identificador exibido na UI e salvo nas métricas (ex.: "Huffman")
    name: str = "base"

    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Recebe bytes (saída da etapa de criptografia localizada) e
        retorna os bytes comprimidos."""
        raise NotImplementedError

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Reverte compress(): recebe bytes comprimidos e retorna os
        bytes originais (ainda com a criptografia localizada presente)."""
        raise NotImplementedError
