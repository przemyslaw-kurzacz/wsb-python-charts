from dataclasses import asdict
import json
import os

from flask import Blueprint, Response, jsonify, request, session, current_app

from app.services.csv_profile import profile_csv_upload
bp = Blueprint("data", __name__, url_prefix="/data")

#1
@bp.route("/profile", methods=["POST"])
def profile_csv():
    """
    Upload a CSV and return:
    - meta (encoding/delimiter/row counts)
    - schema (column types + suggestions)
    - preview rows
    """
    if "file" not in request.files:
        return jsonify({"errors": ["No file field named 'file'"]}), 400

    f = request.files["file"]
    if not f or not getattr(f, "filename", ""):
        return jsonify({"errors": ["No file selected"]}), 400

    result = profile_csv_upload(f)

    payload = asdict(result)  # CsvProfileResult dataclass -> dict
    status = 200 if not result.errors else 400
    return jsonify(payload), status


@bp.route("/current.json", methods=["GET"])
def current_json():
    """Return chart-ready JSON for the currently uploaded CSV (opens nicely in a new tab)."""
    username = session.get("username")
    if not username:
        return jsonify({"errors": ["Not authenticated"]}), 401

    user_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], username)
    if not os.path.isdir(user_folder):
        return jsonify({"errors": ["No uploaded file found for this user"]}), 404

    # Only one CSV is allowed; pick the first.
    csv_files = [f for f in os.listdir(user_folder) if f.lower().endswith(".csv")]
    if not csv_files:
        return jsonify({"errors": ["No uploaded file found for this user"]}), 404

    filename = sorted(csv_files)[0]
    path = os.path.join(user_folder, filename)

    # Profile/parse the stored file.
    with open(path, "rb") as f:
        result = profile_csv_upload(f)

    payload = asdict(result)
    payload["current_file"] = filename

    # Pretty JSON for readability in a blank browser tab.
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(body, mimetype="application/json")
