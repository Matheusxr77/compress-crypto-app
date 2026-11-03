"""Persistência leve e append-only das métricas do pipeline."""

import csv
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List


_LOCK = threading.Lock()
_FIELDS = [
    "timestamp", "doc_id", "direction", "method", "stage",
    "duration_seconds", "input_bytes", "output_bytes",
    "compression_ratio", "throughput_bytes_per_second",
    "original_bytes", "compressed_bytes", "compression_rate",
    "factor_compression", "space_saving_percent", "space_saving_original_percent",
    "space_saving_encrypted_percent", "bits_per_character",
    "compression_throughput_bytes_per_second",
    "decompression_throughput_bytes_per_second", "temporal_asymmetry",
    "peak_memory_bytes", "net_bytes_gain", "expansion_risk_bytes",
    "original_file_bytes", "encrypted_file_bytes",
    "compressed_file_bytes",
    "ratio_original_compressed", "ratio_encrypted_compressed",
    "ratio_original_encrypted", "space_saving_original_encrypted_percent",
]


def metrics_path(folder: str) -> str:
    return os.path.join(folder, "metrics.csv")


def append_metric(folder: str, values: Dict[str, object]) -> None:
    path = metrics_path(folder)
    os.makedirs(folder, exist_ok=True)
    row = {field: values.get(field, "") for field in _FIELDS}
    row["timestamp"] = row["timestamp"] or datetime.now(timezone.utc).isoformat()
    with _LOCK:
        exists = os.path.exists(path) and os.path.getsize(path) > 0
        if exists:
            with open(path, newline="", encoding="utf-8") as existing_stream:
                existing_fields = next(csv.reader(existing_stream), [])
            if existing_fields != _FIELDS:
                with open(path, newline="", encoding="utf-8") as existing_stream:
                    old_rows = list(csv.DictReader(existing_stream))
                with open(path, "w", newline="", encoding="utf-8") as migrated_stream:
                    writer = csv.DictWriter(migrated_stream, fieldnames=_FIELDS)
                    writer.writeheader()
                    writer.writerows(old_rows)
                exists = True
        with open(path, "a", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=_FIELDS)
            if not exists:
                writer.writeheader()
            writer.writerow(row)


def read_metrics(folder: str) -> List[Dict[str, str]]:
    path = metrics_path(folder)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))
