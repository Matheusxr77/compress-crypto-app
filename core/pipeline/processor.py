"""Orquestração do processamento e da reversão de documentos."""

import json
import os
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

from core.compression.registry import get_compressor
from core.crypto.keyword_locator import decrypt_keywords, encrypt_keywords
from core.extractors.registry import extract_text
from core.metrics.repository import append_metric
from core.exporters.pdf_writer import write_text_pdf
from core.exporters.docx_writer import write_text_docx


def _write_text(path: str, value: str) -> None:
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(value)


def _compress_one(
    method: str,
    encrypted: bytes,
    original_file_size: int,
    package_dir: str,
    doc_id: str,
    metrics_folder: str,
) -> Dict[str, object]:
    original_size = len(encrypted)
    tracemalloc.start()
    started = time.perf_counter()
    compressed = get_compressor(method).compress(encrypted)
    compression_duration = time.perf_counter() - started
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    decompress_started = time.perf_counter()
    restored = get_compressor(method).decompress(compressed)
    decompression_duration = time.perf_counter() - decompress_started
    compressed_size = len(compressed)
    lossless = restored == encrypted
    package_path = os.path.join(package_dir, f"{method}.bin")
    with open(package_path, "wb") as stream:
        stream.write(compressed)
    append_metric(metrics_folder, {
        "doc_id": doc_id,
        "direction": "forward",
        "method": method,
        "stage": "compression",
        "duration_seconds": f"{compression_duration:.9f}",
        "input_bytes": original_size,
        "output_bytes": compressed_size,
        "compression_ratio": f"{compressed_size / original_size:.6f}" if original_size else 0,
        "throughput_bytes_per_second": f"{original_size / compression_duration:.3f}" if compression_duration else 0,
        "original_bytes": original_size,
        "compressed_bytes": compressed_size,
        "compression_rate": f"{original_size / compressed_size:.6f}" if compressed_size else 0,
        "factor_compression": f"{original_size / compressed_size:.6f}" if compressed_size else 0,
        "space_saving_percent": f"{(1 - compressed_size / original_size) * 100:.6f}" if original_size else 0,
        "space_saving_original_percent": f"{(1 - compressed_size / original_file_size) * 100:.6f}" if original_file_size else 0,
        "space_saving_encrypted_percent": f"{(1 - compressed_size / original_size) * 100:.6f}" if original_size else 0,
        "bits_per_character": f"{8 * compressed_size / original_size:.6f}" if original_size else 0,
        "compression_throughput_bytes_per_second": f"{original_size / compression_duration:.3f}" if compression_duration else 0,
        "decompression_throughput_bytes_per_second": f"{original_size / decompression_duration:.3f}" if decompression_duration else 0,
        "temporal_asymmetry": f"{compression_duration / decompression_duration:.6f}" if decompression_duration else 0,
        "peak_memory_bytes": peak_memory,
        "net_bytes_gain": original_size - compressed_size,
        "expansion_risk_bytes": max(compressed_size - original_size, 0),
        "original_file_bytes": original_file_size,
        "encrypted_file_bytes": original_size,
        "compressed_file_bytes": compressed_size,
        "ratio_original_compressed": f"{original_file_size / compressed_size:.6f}" if compressed_size else 0,
        "ratio_encrypted_compressed": f"{original_size / compressed_size:.6f}" if compressed_size else 0,
        "ratio_original_encrypted": f"{original_file_size / original_size:.6f}" if original_size else 0,
        "space_saving_original_encrypted_percent": f"{(1 - original_size / original_file_size) * 100:.6f}" if original_file_size else 0,
    })
    return {
        "method": method,
        "path": package_path,
        "compressed_bytes": len(compressed),
        "duration_seconds": compression_duration,
    }


def process_file(
    raw_path: str,
    doc_id: str,
    filename: str,
    keywords: List[str],
    methods: List[str],
    key: str,
    config: Dict[str, str],
) -> Dict[str, object]:
    """Executa extração, criptografia localizada e compressão concorrente."""
    doc_dir = os.path.join(config["UPLOAD_FOLDER"], doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    started = time.perf_counter()
    extracted = extract_text(raw_path)
    extraction_duration = time.perf_counter() - started
    extracted_path = os.path.join(doc_dir, "extracted.txt")
    _write_text(extracted_path, extracted)

    encrypted_started = time.perf_counter()
    encrypted_text, blocks = encrypt_keywords(extracted, keywords, key)
    encrypted_duration = time.perf_counter() - encrypted_started
    encrypted_path = os.path.join(config["ENCRYPTED_FOLDER"], f"{doc_id}.txt")
    _write_text(encrypted_path, encrypted_text)
    encrypted_bytes = encrypted_text.encode("utf-8")

    append_metric(config["METRICS_FOLDER"], {
        "doc_id": doc_id, "direction": "forward", "method": "pipeline",
        "stage": "extraction", "duration_seconds": f"{extraction_duration:.9f}",
        "input_bytes": os.path.getsize(raw_path), "output_bytes": len(extracted.encode("utf-8")),
        "throughput_bytes_per_second": f"{os.path.getsize(raw_path) / extraction_duration:.3f}" if extraction_duration else 0,
    })
    append_metric(config["METRICS_FOLDER"], {
        "doc_id": doc_id, "direction": "forward", "method": "pipeline",
        "stage": "encryption", "duration_seconds": f"{encrypted_duration:.9f}",
        "input_bytes": len(extracted.encode("utf-8")), "output_bytes": len(encrypted_bytes),
        "throughput_bytes_per_second": f"{len(extracted.encode('utf-8')) / encrypted_duration:.3f}" if encrypted_duration else 0,
    })

    package_dir = os.path.join(config["COMPRESSED_FOLDER"], doc_id)
    os.makedirs(package_dir, exist_ok=True)
    worker = lambda method: _compress_one(
        method, encrypted_bytes, os.path.getsize(raw_path),
        package_dir, doc_id, config["METRICS_FOLDER"]
    )
    with ThreadPoolExecutor(max_workers=min(8, len(methods))) as executor:
        packages = list(executor.map(worker, methods))

    metadata = {
        "doc_id": doc_id,
        "filename": filename,
        "keywords": keywords,
        "methods": methods,
        "extracted_path": extracted_path,
        "encrypted_path": encrypted_path,
        "packages": {item["method"]: item["path"] for item in packages},
        "blocks": [block._asdict() for block in blocks],
    }
    with open(os.path.join(doc_dir, "metadata.json"), "w", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
    return {**metadata, "key": key, "extracted_text": extracted, "encrypted_text": encrypted_text}


def list_documents(upload_folder: str) -> List[Dict[str, object]]:
    documents = []
    if not os.path.isdir(upload_folder):
        return documents
    for doc_id in sorted(os.listdir(upload_folder), reverse=True):
        metadata_path = os.path.join(upload_folder, doc_id, "metadata.json")
        if os.path.isfile(metadata_path):
            with open(metadata_path, encoding="utf-8") as stream:
                documents.append(json.load(stream))
    return documents


def reverse_file(
    doc_id: str,
    method: str,
    key: str,
    config: Dict[str, str],
) -> Dict[str, object]:
    metadata_path = os.path.join(config["UPLOAD_FOLDER"], doc_id, "metadata.json")
    if not os.path.isfile(metadata_path):
        raise ValueError("Documento processado não encontrado.")
    with open(metadata_path, encoding="utf-8") as stream:
        metadata = json.load(stream)
    if method == "Todos":
        methods = list(metadata["packages"])
        with ThreadPoolExecutor(max_workers=min(8, len(methods))) as executor:
            results = list(executor.map(
                lambda selected: reverse_file(doc_id, selected, key, config),
                methods,
            ))
        first = results[0]
        first["methods"] = methods
        first["method"] = methods[0]
        return first
    package_path = metadata["packages"].get(method)
    if not package_path or not os.path.isfile(package_path):
        raise ValueError("Método de compressão não encontrado para este documento.")

    with open(package_path, "rb") as stream:
        package = stream.read()
    started = time.perf_counter()
    encrypted = get_compressor(method).decompress(package)
    decompression_duration = time.perf_counter() - started
    decrypt_started = time.perf_counter()
    restored_text = decrypt_keywords(encrypted.decode("utf-8"), key)
    decryption_duration = time.perf_counter() - decrypt_started
    original_extension = os.path.splitext(metadata["filename"])[1].lower()
    restored_extension = original_extension if original_extension in {".pdf", ".docx"} else ".txt"
    restored_path = os.path.join(
        config["RESTORED_FOLDER"], f"{doc_id}_{method}_restored{restored_extension}"
    )
    if restored_extension == ".pdf":
        write_text_pdf(restored_path, restored_text)
    elif restored_extension == ".docx":
        write_text_docx(restored_path, restored_text)
    else:
        _write_text(restored_path, restored_text)
    original_file_size = os.path.getsize(
        os.path.join(config["UPLOAD_FOLDER"], doc_id, metadata["filename"])
    )
    append_metric(config["METRICS_FOLDER"], {
        "doc_id": doc_id, "direction": "reverse", "method": method,
        "stage": "decompression", "duration_seconds": f"{decompression_duration:.9f}",
        "input_bytes": len(package), "output_bytes": len(encrypted),
        "compression_ratio": f"{len(encrypted) / len(package):.6f}" if package else 0,
        "throughput_bytes_per_second": f"{len(package) / decompression_duration:.3f}" if decompression_duration else 0,
        "original_file_bytes": original_file_size,
        "encrypted_file_bytes": len(encrypted),
        "compressed_file_bytes": len(package),
        "ratio_original_compressed": f"{original_file_size / len(package):.6f}" if package else 0,
        "ratio_encrypted_compressed": f"{len(encrypted) / len(package):.6f}" if package else 0,
    })
    append_metric(config["METRICS_FOLDER"], {
        "doc_id": doc_id, "direction": "reverse", "method": method,
        "stage": "decryption", "duration_seconds": f"{decryption_duration:.9f}",
        "input_bytes": len(encrypted), "output_bytes": len(restored_text.encode("utf-8")),
        "throughput_bytes_per_second": f"{len(encrypted) / decryption_duration:.3f}" if decryption_duration else 0,
    })
    return {"metadata": metadata, "restored_text": restored_text, "restored_path": restored_path}
