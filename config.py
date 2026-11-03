"""
config.py - Configurações centrais da aplicação.

Centraliza caminhos de pastas, limites de upload e parâmetros globais,
mantendo a estrutura de diretórios desacoplada do código de rotas.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-troque-em-producao")

    # --- Pastas dinâmicas do pipeline -----------------------------------
    # uploads/     -> arquivos originais enviados pelo usuário (.txt/.pdf/.docx)
    # encrypted/   -> arquivos com a criptografia localizada já aplicada
    # compressed/  -> pacotes finais, um subdiretório por método de compressão
    # restored/    -> arquivos reconstruídos pelo processo de reversão
    # metrics/     -> CSV/SQLite consolidado com as métricas de todas as etapas
    UPLOAD_FOLDER = os.path.join(STORAGE_DIR, "uploads")
    ENCRYPTED_FOLDER = os.path.join(STORAGE_DIR, "encrypted")
    COMPRESSED_FOLDER = os.path.join(STORAGE_DIR, "compressed")
    RESTORED_FOLDER = os.path.join(STORAGE_DIR, "restored")
    METRICS_FOLDER = os.path.join(STORAGE_DIR, "metrics")

    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB por upload
    ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

    # Nomes padronizados dos 10 métodos de compressão sem perdas.
    # Cada nome corresponde a um codec registrado em
    # core/compression/registry.py.
    COMPRESSION_METHODS = [
        "Huffman", "Arithmetic", "BWT", "Golomb", "LZ77",
        "LZMA", "LZW", "PAQ", "PPM", "RLE",
    ]
