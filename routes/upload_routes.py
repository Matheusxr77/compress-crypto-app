"""Rotas do processamento central."""

import os
import uuid
from typing import List

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from core.crypto.cipher import generate_key
from core.pipeline.processor import process_file

upload_bp = Blueprint("upload", __name__)


def _parse_keywords(raw: str) -> List[str]:
    return [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


@upload_bp.route("/", methods=["GET", "POST"])
def index():
    methods = current_app.config["COMPRESSION_METHODS"]
    if request.method == "GET":
        return render_template("upload.html", active_tab="upload", compression_methods=methods)

    uploaded = request.files.get("arquivo")
    keywords = _parse_keywords(request.form.get("palavras_chave", ""))
    selected = request.form.get("metodo_compressao", "Todos")
    if uploaded is None or not uploaded.filename:
        flash("Selecione um arquivo (.txt, .pdf ou .docx).", "error")
        return redirect(url_for("upload.index"))
    filename = secure_filename(uploaded.filename)
    if not _allowed_file(filename):
        flash("Extensão não suportada. Use .txt, .pdf ou .docx.", "error")
        return redirect(url_for("upload.index"))
    if selected != "Todos" and selected not in methods:
        flash("Método de compressão inválido.", "error")
        return redirect(url_for("upload.index"))

    doc_id = uuid.uuid4().hex[:12]
    doc_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], doc_id)
    os.makedirs(doc_dir, exist_ok=True)
    raw_path = os.path.join(doc_dir, filename)
    uploaded.save(raw_path)
    key = generate_key()
    selected_methods = methods if selected == "Todos" else [selected]
    try:
        result = process_file(
            raw_path, doc_id, filename, keywords, selected_methods, key, current_app.config
        )
    except (OSError, ValueError, RuntimeError) as exc:
        flash(f"Não foi possível processar o arquivo: {exc}", "error")
        return redirect(url_for("upload.index"))

    result["selected_method"] = selected
    result["compression_methods"] = selected_methods
    result["texto_original"] = result["extracted_text"]
    result["texto_cifrado"] = result["encrypted_text"]
    result["chave"] = result["key"]
    result["total_blocos"] = len(result["blocks"])
    result["blocos"] = result["blocks"]
    result["filename"] = filename
    result["keywords"] = keywords
    if keywords:
        flash(
            f"Arquivo processado com sucesso (id {doc_id}). Guarde a chave para a reversão.",
            "success",
        )
    else:
        flash(
            f"Arquivo comprimido com sucesso (id {doc_id}), sem criptografia localizada.",
            "success",
        )
    return render_template(
        "upload.html",
        active_tab="upload",
        compression_methods=methods,
        result=result,
    )
