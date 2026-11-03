import json
import os

from flask import Blueprint, current_app, abort, render_template

from core.pipeline.processor import list_documents

inspection_bp = Blueprint("inspection", __name__)


@inspection_bp.route("/inspecao")
def index():
    return render_template(
        "inspection.html",
        active_tab="inspecao",
        documents=list_documents(current_app.config["UPLOAD_FOLDER"]),
    )


@inspection_bp.route("/inspecao/<doc_id>")
def detail(doc_id: str):
    metadata_path = os.path.join(current_app.config["UPLOAD_FOLDER"], doc_id, "metadata.json")
    if not os.path.isfile(metadata_path):
        abort(404)
    with open(metadata_path, encoding="utf-8") as stream:
        document = json.load(stream)
    with open(document["extracted_path"], encoding="utf-8") as stream:
        document["extracted_text"] = stream.read()
    with open(document["encrypted_path"], encoding="utf-8") as stream:
        document["encrypted_text"] = stream.read()
    packages = {}
    for method, path in document["packages"].items():
        with open(path, "rb") as stream:
            packages[method] = stream.read(128).hex(" ")
    document["packages_preview"] = packages
    return render_template("inspection.html", active_tab="inspecao", documents=[document], document=document)
