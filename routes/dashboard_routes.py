import os
import shutil
from collections import defaultdict

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from core.metrics.repository import clear_metrics, read_metrics

dashboard_bp = Blueprint("dashboard", __name__)


def _clear_storage() -> None:
    """Remove os artefatos gerados, mantendo a estrutura de pastas disponível."""
    folders = (
        current_app.config["UPLOAD_FOLDER"],
        current_app.config["ENCRYPTED_FOLDER"],
        current_app.config["COMPRESSED_FOLDER"],
        current_app.config["RESTORED_FOLDER"],
    )
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        for entry in os.scandir(folder):
            if entry.is_dir():
                shutil.rmtree(entry.path)
            else:
                os.remove(entry.path)
    clear_metrics(current_app.config["METRICS_FOLDER"])


@dashboard_bp.route("/dashboard", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            _clear_storage()
        except OSError as exc:
            flash(f"Não foi possível limpar os arquivos armazenados: {exc}", "error")
        else:
            flash("Arquivos armazenados e métricas removidos com sucesso.", "success")
        return redirect(url_for("dashboard.index"))

    metrics = read_metrics(current_app.config["METRICS_FOLDER"])
    grouped = defaultdict(lambda: {
        "compression": 0.0, "decompression": 0.0, "throughput": 0.0, "count": 0,
        "original_bytes": 0, "compressed_bytes": 0, "compression_rate": 0.0,
        "space_saving_percent": 0.0, "peak_memory_bytes": 0,
        "space_saving_original_percent": 0.0,
        "space_saving_encrypted_percent": 0.0,
        "encrypted_file_bytes": 0,
        "ratio_original_compressed": 0.0, "ratio_encrypted_compressed": 0.0,
        "ratio_original_encrypted": 0.0,
        "space_saving_original_encrypted_percent": 0.0,
    })
    for row in metrics:
        method = row.get("method", "pipeline")
        if method == "pipeline":
            continue
        item = grouped[method]
        item["count"] += 1
        duration = float(row.get("duration_seconds") or 0)
        if row.get("stage") == "compression":
            item["compression"] += duration
        if row.get("stage") == "decompression":
            item["decompression"] += duration
        item["throughput"] += float(row.get("throughput_bytes_per_second") or 0)
        if row.get("stage") == "compression" and row.get("original_file_bytes"):
            original_bytes = int(float(row["original_file_bytes"]))
            compressed_bytes = int(float(row.get("compressed_file_bytes") or 0))
            encrypted_bytes = int(float(row.get("encrypted_file_bytes") or 0))
            item["original_bytes"] += original_bytes
            item["compressed_bytes"] += compressed_bytes
            item["encrypted_file_bytes"] += encrypted_bytes
            item["ratio_original_compressed"] = item["original_bytes"] / item["compressed_bytes"] if item["compressed_bytes"] else 0
            item["ratio_encrypted_compressed"] = item["encrypted_file_bytes"] / item["compressed_bytes"] if item["compressed_bytes"] else 0
            item["ratio_original_encrypted"] = item["original_bytes"] / item["encrypted_file_bytes"] if item["encrypted_file_bytes"] else 0
            item["space_saving_original_percent"] = (1 - item["compressed_bytes"] / item["original_bytes"]) * 100 if item["original_bytes"] else 0
            item["space_saving_encrypted_percent"] = (1 - item["compressed_bytes"] / item["encrypted_file_bytes"]) * 100 if item["encrypted_file_bytes"] else 0
            item["space_saving_original_encrypted_percent"] = (1 - item["encrypted_file_bytes"] / item["original_bytes"]) * 100 if item["original_bytes"] else 0
            item["space_saving_percent"] = item["space_saving_original_percent"]
            item["compression_rate"] = item["ratio_original_compressed"]
            item["peak_memory_bytes"] = max(item["peak_memory_bytes"], int(float(row.get("peak_memory_bytes") or 0)))
    dashboard = [{"method": method, **values} for method, values in sorted(grouped.items())]
    return render_template("dashboard.html", active_tab="dashboard", dashboard=dashboard, metrics=metrics)
