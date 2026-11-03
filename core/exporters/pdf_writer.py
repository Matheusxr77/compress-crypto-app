"""Escritor PDF mínimo com mapa Unicode para texto reconstruído."""

import os
import re
from typing import Dict


def _escape(value: bytes) -> bytes:
    return value.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _unicode_map(text: str) -> bytes:
    used = sorted(set(text.encode("cp1252", errors="replace")))
    entries = []
    for value in used:
        character = bytes((value,)).decode("cp1252")
        codepoint = character.encode("utf-16-be").hex().upper()
        entries.append(f"<{value:02X}> <{codepoint}>")
    cmap = [
        "/CIDInit /ProcSet findresource begin",
        "12 dict begin begincmap",
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
        "/CMapName /Adobe-Identity-UCS def /CMapType 2 def",
        "1 begincodespacerange <00> <FF> endcodespacerange",
        f"{len(entries)} beginbfchar",
        *entries,
        "endbfchar endcmap CMapName currentdict /CMap defineresource pop end end",
    ]
    return "\n".join(cmap).encode("ascii")


def write_text_pdf(path: str, text: str) -> None:
    """Cria um PDF simples com o texto fornecido, quebrando linhas longas."""
    lines = []
    for raw_line in text.splitlines() or [""]:
        lines.extend(re.findall(r".{1,95}(?:\s+|$)", raw_line) or [""])
    lines = lines or [""]
    pages = [lines[index:index + 48] for index in range(0, len(lines), 48)]

    encoded_text = text.encode("cp1252", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding /ToUnicode 6 0 R >>",
    ]
    content = ["BT", "/F1 11 Tf", "50 750 Td", "14 TL"]
    for line in pages[0]:
        content.append(f"({_escape(line.encode('cp1252', errors='replace')) .decode('latin-1')}) Tj")
        content.append("0 -14 Td")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1")
    objects.append(
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
    )
    cmap = _unicode_map(text)
    objects.append(
        b"<< /Length " + str(len(cmap)).encode() + b" >>\nstream\n" + cmap + b"\nendstream"
    )

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as stream_file:
        stream_file.write(output)
