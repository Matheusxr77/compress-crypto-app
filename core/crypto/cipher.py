"""
cipher.py - Wrapper de criptografia simétrica usado para cifrar os
blocos de texto localizados pela busca de palavras-chave.

Usa Fernet (da biblioteca `cryptography`), que implementa AES-128 em
modo CBC com autenticação HMAC-SHA256 — atendendo ao requisito de usar
AES/Fernet com uma API simples e segura (token autenticado, resistente
a adulteração).
"""

from cryptography.fernet import Fernet, InvalidToken


def generate_key() -> str:
    """Gera uma nova chave Fernet (string base64 url-safe de 44 chars).

    Uma chave por upload: o usuário deve guardá-la para a reversão.
    O sistema não a persiste em nenhum momento.
    """
    return Fernet.generate_key().decode("utf-8")


def encrypt_text(plain_text: str, key: str) -> str:
    """Cifra uma string e devolve o token Fernet (string)."""
    fernet = Fernet(key.encode("utf-8"))
    token = fernet.encrypt(plain_text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(token: str, key: str) -> str:
    """Decifra um token Fernet.

    Lança ValueError se a chave estiver incorreta ou o token tiver sido
    corrompido/adulterado (Fernet verifica a autenticidade via HMAC).
    """
    fernet = Fernet(key.encode("utf-8"))
    try:
        plain_bytes = fernet.decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Chave incorreta ou dado corrompido.") from exc
    return plain_bytes.decode("utf-8")
