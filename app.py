import io
import os
import tempfile
import pandas as pd
from flask import Flask, request, render_template, jsonify, send_file
from checker_logic import validate_catalog_file
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/check_catalog", methods=["POST"])
def check_catalog():
    if "catalog_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    check_type = request.form.get("check_type", "ALL IN ONE")
    file = request.files["catalog_file"]

    try:
        file_buffer = io.BytesIO(file.read())
        errors = validate_catalog_file(file_buffer, check_mode=check_type)

        if errors:
            return jsonify({"status": "issues_found", "errors": errors})
        return jsonify({"status": "success", "message": f"No errors found for {check_type}!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download_errors", methods=["POST"])
def download_errors():
    data = request.get_json()
    errors = data.get("errors", [])
    original_filename = data.get("filename", "Catalog")

    df = pd.DataFrame(errors)
    df = df.rename(columns={
        "ID": "EEP Master Catalog Number",
        "Title": "Title",
        "Issue": "Issues"
    })

    df = df[["EEP Master Catalog Number", "Title", "Issues"]]

    base = os.path.splitext(original_filename)[0]
    date = datetime.now().strftime("%Y-%m-%d")
    filename = f"{base} Error Checked {date}.xlsx"

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Validation Issues")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
