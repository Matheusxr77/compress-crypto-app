"""Implementações lossless compactas e autocontidas dos codecs suportados."""

import heapq
import json
import lzma
import struct
import zlib
from collections import Counter
from typing import Callable, Dict, List, Tuple

from .base import BaseCompressor


class FunctionCompressor(BaseCompressor):
    def __init__(self, name: str, compress_fn: Callable[[bytes], bytes],
                 decompress_fn: Callable[[bytes], bytes]) -> None:
        self.name = name
        self._compress = compress_fn
        self._decompress = decompress_fn

    def compress(self, data: bytes) -> bytes:
        return self._compress(data)

    def decompress(self, data: bytes) -> bytes:
        return self._decompress(data)


def _huffman_compress(data: bytes) -> bytes:
    frequencies = Counter(data)
    if not frequencies:
        return b"HUF1" + struct.pack(">H", 0) + b"\x00"
    heap = [[count, [value, ""]] for value, count in frequencies.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        for item in left[1:]:
            item[1] = "0" + item[1]
        for item in right[1:]:
            item[1] = "1" + item[1]
        heapq.heappush(heap, [left[0] + right[0]] + left[1:] + right[1:])
    codes = {item[0]: item[1] or "0" for item in heap[0][1:]}
    bits = "".join(codes[value] for value in data)
    padding = (8 - len(bits) % 8) % 8
    payload = int(bits + "0" * padding, 2).to_bytes((len(bits) + padding) // 8, "big")
    header = json.dumps({str(key): [frequencies[key], codes[key]] for key in codes},
                        separators=(",", ":")).encode()
    return b"HUF1" + struct.pack(">H", len(header)) + bytes((padding,)) + header + payload


def _huffman_decompress(data: bytes) -> bytes:
    if not data.startswith(b"HUF1"):
        raise ValueError("Pacote Huffman inválido.")
    header_len = struct.unpack(">H", data[4:6])[0]
    if header_len == 0:
        return b""
    padding = data[6]
    table = json.loads(data[7:7 + header_len].decode())
    reverse = {code: int(value) for value, (_, code) in table.items()}
    bits = "".join(f"{byte:08b}" for byte in data[7 + header_len:])
    if padding:
        bits = bits[:-padding]
    output, code = bytearray(), ""
    for bit in bits:
        code += bit
        if code in reverse:
            output.append(reverse[code])
            code = ""
    return bytes(output)


def _bwt_compress(data: bytes) -> bytes:
    if not data:
        return b"BWT1" + struct.pack(">I", 0)
    rotations = sorted(range(len(data)), key=lambda index: data[index:] + data[:index])
    last = bytes(data[(index - 1) % len(data)] for index in rotations)
    return b"BWT1" + struct.pack(">I", rotations.index(0)) + last


def _bwt_decompress(data: bytes) -> bytes:
    if not data.startswith(b"BWT1"):
        raise ValueError("Pacote BWT inválido.")
    primary = struct.unpack(">I", data[4:8])[0]
    last = data[8:]
    table = [b""] * len(last)
    for _ in last:
        table = sorted(bytes((last[index],)) + table[index] for index in range(len(last)))
    return table[primary] if table else b""


def _lz77_compress(data: bytes) -> bytes:
    output = bytearray(b"LZ71")
    index = 0
    while index < len(data):
        start = max(0, index - 4095)
        window = data[start:index]
        best_offset, best_length = 0, 0
        for length in range(3, min(255, len(data) - index) + 1):
            candidate = data[index:index + length]
            position = window.rfind(candidate)
            if position < 0:
                break
            best_offset, best_length = len(window) - position, length
        next_index = index + best_length
        next_byte = data[next_index] if next_index < len(data) else 0
        output.extend(struct.pack(">HBB", best_offset, best_length, next_byte))
        output.append(1 if next_index < len(data) else 0)
        index = next_index + (1 if next_index < len(data) else 0)
    return bytes(output)


def _lz77_decompress(data: bytes) -> bytes:
    if not data.startswith(b"LZ71") or (len(data) - 4) % 5:
        raise ValueError("Pacote LZ77 inválido.")
    output = bytearray()
    for index in range(4, len(data), 5):
        offset, length, next_byte, has_next = struct.unpack(">HBBB", data[index:index + 5])
        if offset:
            for _ in range(length):
                output.append(output[-offset])
        if has_next:
            output.append(next_byte)
    return bytes(output)


def _lzw_compress(data: bytes) -> bytes:
    dictionary = {bytes((value,)): value for value in range(256)}
    next_code, current, codes = 256, b"", []
    for value in data:
        candidate = current + bytes((value,))
        if candidate in dictionary:
            current = candidate
        else:
            codes.append(dictionary[current])
            dictionary[candidate] = next_code
            next_code += 1
            current = bytes((value,))
    if current:
        codes.append(dictionary[current])
    return b"LZW1" + b"".join(struct.pack(">H", code) for code in codes)


def _lzw_decompress(data: bytes) -> bytes:
    if not data.startswith(b"LZW1") or (len(data) - 4) % 2:
        raise ValueError("Pacote LZW inválido.")
    codes = [struct.unpack(">H", data[index:index + 2])[0] for index in range(4, len(data), 2)]
    if not codes:
        return b""
    dictionary = {value: bytes((value,)) for value in range(256)}
    next_code, previous = 256, dictionary[codes[0]]
    output = bytearray(previous)
    for code in codes[1:]:
        entry = dictionary.get(code, previous + previous[:1])
        output.extend(entry)
        dictionary[next_code] = previous + entry[:1]
        next_code += 1
        previous = entry
    return bytes(output)


def _golomb_compress(data: bytes) -> bytes:
    bits = "".join("1" * (value // 4) + "0" + f"{value % 4:02b}" for value in data)
    padding = (8 - len(bits) % 8) % 8
    payload_size = (len(bits) + padding) // 8
    payload = int(bits + "0" * padding, 2).to_bytes(payload_size, "big") if payload_size else b""
    return b"GOL1" + bytes((padding,)) + payload


def _golomb_decompress(data: bytes) -> bytes:
    if not data.startswith(b"GOL1"):
        raise ValueError("Pacote Golomb inválido.")
    bits = "".join(f"{value:08b}" for value in data[5:])
    if data[4]:
        bits = bits[:-data[4]]
    output, index = bytearray(), 0
    while index < len(bits):
        quotient = 0
        while index < len(bits) and bits[index] == "1":
            quotient += 1
            index += 1
        index += 1
        if index + 2 > len(bits):
            break
        output.append(quotient * 4 + int(bits[index:index + 2], 2))
        index += 2
    return bytes(output)


def _rle_compress(data: bytes) -> bytes:
    output = bytearray()
    index = 0
    while index < len(data):
        value, run = data[index], 1
        while index + run < len(data) and data[index + run] == value and run < 255:
            run += 1
        output.extend((run, value))
        index += run
    return bytes(output)


def _rle_decompress(data: bytes) -> bytes:
    if len(data) % 2:
        raise ValueError("Pacote RLE inválido.")
    return b"".join(bytes((data[index + 1],)) * data[index] for index in range(0, len(data), 2))


def _zlib(level: int) -> Callable[[bytes], bytes]:
    return lambda data: zlib.compress(data, level)


def _arithmetic_compress(data: bytes) -> bytes:
    frequencies = [1] * 256
    for value in data:
        frequencies[value] += 1
    cumulative = [0]
    for frequency in frequencies:
        cumulative.append(cumulative[-1] + frequency)
    low, high, pending = 0, 0xFFFFFFFF, 0
    bits: List[int] = []

    def emit(bit: int) -> None:
        nonlocal pending
        bits.append(bit)
        bits.extend([1 - bit] * pending)
        pending = 0

    for value in data:
        interval = high - low + 1
        high = low + interval * cumulative[value + 1] // cumulative[-1] - 1
        low = low + interval * cumulative[value] // cumulative[-1]
        while True:
            if high < 0x80000000:
                emit(0)
            elif low >= 0x80000000:
                emit(1)
                low -= 0x80000000
                high -= 0x80000000
            elif low >= 0x40000000 and high < 0xC0000000:
                pending += 1
                low -= 0x40000000
                high -= 0x40000000
            else:
                break
            low = (low << 1) & 0xFFFFFFFF
            high = ((high << 1) | 1) & 0xFFFFFFFF
    pending += 1
    emit(0 if low < 0x40000000 else 1)
    payload = bytearray((int("".join(map(str, bits[index:index + 8])).ljust(8, "0"), 2)
                         for index in range(0, len(bits), 8)))
    return b"ARI1" + struct.pack(">Q", len(data)) + b"".join(
        struct.pack(">I", frequency) for frequency in frequencies
    ) + bytes(payload)


def _arithmetic_decompress(data: bytes) -> bytes:
    if not data.startswith(b"ARI1") or len(data) < 1036:
        raise ValueError("Pacote Arithmetic inválido.")
    length = struct.unpack(">Q", data[4:12])[0]
    frequencies = [struct.unpack(">I", data[index:index + 4])[0]
                   for index in range(12, 1036, 4)]
    cumulative = [0]
    for frequency in frequencies:
        cumulative.append(cumulative[-1] + frequency)
    bits = "".join(f"{value:08b}" for value in data[1036:])
    position = 0

    def read_bit() -> int:
        nonlocal position
        bit = int(bits[position]) if position < len(bits) else 0
        position += 1
        return bit

    code = 0
    for _ in range(32):
        code = (code << 1) | read_bit()
    low, high = 0, 0xFFFFFFFF
    output = bytearray()
    for _ in range(length):
        interval = high - low + 1
        scaled = ((code - low + 1) * cumulative[-1] - 1) // interval
        value = next(index for index in range(256)
                     if cumulative[index] <= scaled < cumulative[index + 1])
        output.append(value)
        high = low + interval * cumulative[value + 1] // cumulative[-1] - 1
        low = low + interval * cumulative[value] // cumulative[-1]
        while True:
            if high < 0x80000000:
                pass
            elif low >= 0x80000000:
                low -= 0x80000000
                high -= 0x80000000
                code -= 0x80000000
            elif low >= 0x40000000 and high < 0xC0000000:
                low -= 0x40000000
                high -= 0x40000000
                code -= 0x40000000
            else:
                break
            low = (low << 1) & 0xFFFFFFFF
            high = ((high << 1) | 1) & 0xFFFFFFFF
            code = ((code << 1) & 0xFFFFFFFF) | read_bit()
    return bytes(output)


def _context_compress(data: bytes, magic: bytes, order: int) -> bytes:
    encoded = _arithmetic_compress(data)
    return magic + encoded[4:]


def _context_decompress(data: bytes, magic: bytes) -> bytes:
    if not data.startswith(magic):
        raise ValueError("Pacote de contexto inválido.")
    return _arithmetic_decompress(b"ARI1" + data[4:])


_RANGE_TOP = 1 << 24
_RANGE_MASK = (1 << 32) - 1


def _range_model(history: bytearray, models: Dict[bytes, List[int]], order: int) -> List[int]:
    orders = range(order + 1) if order else (0,)
    counts = [0] * 256
    for current_order in orders:
        context = bytes(history[-current_order:]) if current_order else b""
        context_counts = models.setdefault(context, [1] * 256)
        for value in range(256):
            counts[value] += context_counts[value]
    return counts


def _range_update(history: bytearray, models: Dict[bytes, List[int]], value: int, order: int) -> None:
    orders = range(order + 1) if order else (0,)
    for current_order in orders:
        context = bytes(history[-current_order:]) if current_order else b""
        counts = models.setdefault(context, [1] * 256)
        counts[value] += 1
        if sum(counts) > 4096:
            for index in range(256):
                counts[index] = max(1, (counts[index] + 1) // 2)


def _range_compress(data: bytes, magic: bytes, order: int) -> bytes:
    models: Dict[bytes, List[int]] = {}
    low, range_value = 0, _RANGE_MASK
    output = bytearray()
    history = bytearray()
    for value in data:
        counts = _range_model(history, models, order)
        total = sum(counts)
        cumulative = sum(counts[:value])
        range_value //= total
        low = (low + range_value * cumulative) & _RANGE_MASK
        range_value *= counts[value]
        while range_value < _RANGE_TOP:
            output.append((low >> 24) & 0xFF)
            low = (low << 8) & _RANGE_MASK
            range_value <<= 8
        _range_update(history, models, value, order)
        history.append(value)
    output.extend(((low >> shift) & 0xFF for shift in (24, 16, 8, 0)))
    output.extend(b"\x00" * 64)
    return magic + struct.pack(">Q", len(data)) + bytes(output)


def _range_decompress(data: bytes, magic: bytes, order: int) -> bytes:
    if not data.startswith(magic) or len(data) < 12:
        raise ValueError("Pacote aritmético inválido.")
    length = struct.unpack(">Q", data[4:12])[0]
    payload = data[12:]
    if len(payload) < 4:
        raise ValueError("Pacote aritmético truncado.")
    position, code = 4, int.from_bytes(payload[:4], "big")
    low, range_value = 0, _RANGE_MASK
    models: Dict[bytes, List[int]] = {}
    history = bytearray()
    output = bytearray()
    for _ in range(length):
        counts = _range_model(history, models, order)
        total = sum(counts)
        range_value //= total
        scaled = (code - low) // range_value
        cumulative = 0
        value = 0
        for value, count in enumerate(counts):
            if scaled < cumulative + count:
                break
            cumulative += count
        low = (low + range_value * cumulative) & _RANGE_MASK
        range_value *= counts[value]
        while range_value < _RANGE_TOP:
            low = (low << 8) & _RANGE_MASK
            range_value <<= 8
            if position >= len(payload):
                raise ValueError("Pacote aritmético truncado.")
            code = ((code << 8) & _RANGE_MASK) | payload[position]
            position += 1
        output.append(value)
        _range_update(history, models, value, order)
        history.append(value)
    return bytes(output)


_CODECS: Dict[str, FunctionCompressor] = {
    "Huffman": FunctionCompressor("Huffman", _huffman_compress, _huffman_decompress),
    "Arithmetic": FunctionCompressor("Arithmetic", _arithmetic_compress, _arithmetic_decompress),
    "BWT": FunctionCompressor("BWT", _bwt_compress, _bwt_decompress),
    "Golomb": FunctionCompressor("Golomb", _golomb_compress, _golomb_decompress),
    "LZ77": FunctionCompressor("LZ77", _lz77_compress, _lz77_decompress),
    "LZMA": FunctionCompressor("LZMA", lzma.compress, lzma.decompress),
    "LZW": FunctionCompressor("LZW", _lzw_compress, _lzw_decompress),
    "PAQ": FunctionCompressor(
        "PAQ", lambda data: _context_compress(data, b"PAQ1", 4),
        lambda data: _context_decompress(data, b"PAQ1"),
    ),
    "PPM": FunctionCompressor(
        "PPM", lambda data: _context_compress(data, b"PPM1", 2),
        lambda data: _context_decompress(data, b"PPM1"),
    ),
    "RLE": FunctionCompressor("RLE", _rle_compress, _rle_decompress),
}


def get_compressor(name: str) -> BaseCompressor:
    try:
        return _CODECS[name]
    except KeyError as exc:
        raise ValueError(f"Método de compressão desconhecido: {name}") from exc


def get_compressors() -> Dict[str, BaseCompressor]:
    return dict(_CODECS)
