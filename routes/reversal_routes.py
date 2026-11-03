import os
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for

from core.pipeline.processor import list_documents, reverse_file

reversal_bp = Blueprint("reversal", __name__)


@reversal_bp.route("/reversao", methods=["GET", "POST"])
def index():
    documents = list_documents(current_app.config["UPLOAD_FOLDER"])
    result = None
    if request.method == "POST":
        doc_id = request.form.get("doc_id", "")
        method = request.form.get("method", "")
        key = request.form.get("key", "").strip()
        try:
            result = reverse_file(doc_id, method, key, current_app.config)
            result["doc_id"] = doc_id
            result["method"] = result.get("method", method)
            flash("Arquivo revertido e métricas registradas.", "success")
        except (OSError, ValueError) as exc:
            flash(f"Não foi possível reverter o arquivo: {exc}", "error")
    return render_template("reversal.html", active_tab="reversao", documents=documents, result=result)


@reversal_bp.route("/reversao/download/<doc_id>/<method>")
def download(doc_id: str, method: str):
    documents = list_documents(current_app.config["UPLOAD_FOLDER"])
    document = next((item for item in documents if item["doc_id"] == doc_id), None)
    if document is None:
        return redirect(url_for("reversal.index"))
    if method == "Todos":
        archive = BytesIO()
        with ZipFile(archive, "w", ZIP_DEFLATED) as zip_file:
            for selected_method in document["methods"]:
                extension = os.path.splitext(document["filename"])[1].lower()
                if extension not in {".pdf", ".docx"}:
                    extension = ".txt"
                filename = f"{doc_id}_{selected_method}_restored{extension}"
                path = os.path.join(current_app.config["RESTORED_FOLDER"], filename)
                if os.path.isfile(path):
                    zip_file.write(path, arcname=filename)
        archive.seek(0)
        return send_file(
            archive,
            as_attachment=True,
            download_name=f"{doc_id}_all_methods_restored.zip",
            mimetype="application/zip",
        )
    extension = os.path.splitext(document["filename"])[1].lower()
    if extension not in {".pdf", ".docx"}:
        extension = ".txt"
    filename = f"{doc_id}_{method}_restored{extension}"
    path = os.path.join(current_app.config["RESTORED_FOLDER"], filename)
    return send_file(path, as_attachment=True, download_name=filename)
