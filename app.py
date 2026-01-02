import io
import pandas as pd
import os
import tempfile
from flask import Flask, request, render_template, jsonify
from checker_logic import validate_catalog_file
from flask import send_file
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/check_catalog', methods=['POST'])
def check_catalog():
    if 'catalog_file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['catalog_file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        # Run the validation
        file_buffer = io.BytesIO(file.read())
        errors = validate_catalog_file(file_buffer)
        
        if errors:
            # Return errors to be displayed in the modal
            return jsonify({"status": "issues_found", "errors": errors})
        else:
            return jsonify({"status": "success", "message": "No errors found! The catalog file is valid."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download_errors', methods=['POST'])
def download_errors():
    data = request.get_json()
    errors = data.get('errors', [])
    original_filename = data.get('filename', 'catalog_errors')
    
    # 1. Create DataFrame and map to specific column names
    df = pd.DataFrame(errors)
    df = df.rename(columns={
        "ID": "EEP Master Catalog Number",
        "Title": "Title",
        "Issue": "Issues"
    })

    # 2. Force the specific column order
    # This ensures "EEP Master Catalog Number" is 1st, "Title" is 2nd, "Issues" is 3rd
    df = df[["EEP Master Catalog Number", "Title", "Issues"]]

    # 3. Create the filename: [Original Name] Error Checked [Date].xlsx
    base_name = os.path.splitext(original_filename)[0]
    current_date = datetime.now().strftime("%Y-%m-%d")
    download_name = f"{base_name} Error Checked {current_date}.xlsx"

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Validation Issues')
    
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    
if __name__ == '__main__':
    # Create static folder if it doesn't exist
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True, port=5000)