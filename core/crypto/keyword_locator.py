"""
keyword_locator.py - Localização de palavras-chave no texto e aplicação de criptografia localizada:
a partir da palavra-chave, somente o restante da mesma linha é cifrado.

Formato de marcação reversível
-------------------------------
Cada bloco cifrado substitui, no texto, a frase original pelo marcador:

    \\x02ENC:<token-fernet-base64url>\\x03

Os caracteres de controle \\x02 (STX) e \\x03 (ETX) foram escolhidos por
não aparecerem em texto comum, minimizando colisão com o conteúdo
original. Na reversão, cada marcador é localizado via regex, o token é
decifrado com a chave fornecida e a frase original é recolocada em seu
lugar, remontando o documento original.
"""

import re
from typing import List, NamedTuple, Optional, Tuple

from .cipher import decrypt_text, encrypt_text

_MARK_START = "\x02ENC:"
_MARK_END = "\x03"
_MARKER_RE = re.compile(re.escape(_MARK_START) + r"(?P<token>[^\x03]+)" + re.escape(_MARK_END))


class EncryptedBlock(NamedTuple):
    """Representa um bloco/frase localizado e cifrado."""

    original_text: str
    keyword_matched: str


def _find_keyword(line: str, keywords: List[str]) -> Optional[Tuple[str, int]]:
    matches = [
        (match.start(), keyword)
        for keyword in keywords
        if keyword
        for match in [re.search(re.escape(keyword), line, re.IGNORECASE)]
        if match
    ]
    if not matches:
        return None
    position, keyword = min(matches)
    return keyword, position


def encrypt_keywords(text: str, keywords: List[str], key: str):
    """Cifra o valor após ``:`` quando a palavra-chave for um rótulo.

    Para ``CPF: 123`` o marcador cobre apenas ``123``. Quando não há
    dois-pontos após a palavra-chave, o marcador começa na própria palavra.

    Retorna (texto_resultante, blocos_cifrados):
      - texto_resultante: o texto original com os blocos encontrados
        substituídos pelos marcadores §ENC:...§ (ver docstring do módulo);
      - blocos_cifrados: lista de EncryptedBlock, útil para a UI exibir
        o que foi localizado (Aba 1 / Aba 2).
    """
    keywords = [k.strip() for k in keywords if k.strip()]
    found: List[EncryptedBlock] = []
    result_parts: List[str] = []

    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        ending = line[len(content):]
        match = _find_keyword(content, keywords) if keywords else None
        if match is None:
            result_parts.append(line)
            continue
        matched_kw, position = match
        value_start = position + len(matched_kw)
        while value_start < len(content) and content[value_start].isspace():
            value_start += 1
        if value_start < len(content) and content[value_start] == ":":
            value_start += 1
            while value_start < len(content) and content[value_start].isspace():
                value_start += 1
            localized = content[value_start:]
            visible_prefix = content[:value_start]
        else:
            localized = content[position:]
            visible_prefix = content[:position]
        token = encrypt_text(localized, key)
        result_parts.append(
            visible_prefix + f"{_MARK_START}{token}{_MARK_END}" + ending
        )
        found.append(EncryptedBlock(original_text=localized, keyword_matched=matched_kw))

    return "".join(result_parts), found


def decrypt_keywords(text: str, key: str) -> str:
    """Reverte encrypt_keywords(): localiza cada marcador, decifra o
    token com `key` e recoloca o bloco original em seu lugar.

    Lança ValueError (propagada de cipher.decrypt_text) se a chave for
    incorreta ou algum token estiver corrompido — nesse caso nenhuma
    substituição parcial é aplicada silenciosamente, para não devolver
    um documento parcialmente corrompido sem avisar o usuário.
    """

    def _replace(match: "re.Match") -> str:
        return decrypt_text(match.group("token"), key)

    # Valida todos os tokens antes de montar o resultado final, para que
    # uma chave errada falhe de forma clara em vez de gerar um documento
    # parcialmente decifrado.
    for match in _MARKER_RE.finditer(text):
        decrypt_text(match.group("token"), key)

    return _MARKER_RE.sub(_replace, text)
