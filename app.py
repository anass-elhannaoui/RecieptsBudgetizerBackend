from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image
import pytesseract
import io


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}) # Allow all origins for dev

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\yoga\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/scan", methods=["POST"])
def scan_receipt():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        image = Image.open(file.stream)
        raw_text = pytesseract.image_to_string(image)

        # Parse structured fields from raw_text
        lines = raw_text.splitlines()
        store = lines[0] if lines else "Unknown Store"
        date = ""
        total = 0.0
        tax = 0.0

        for line in lines:
            if "subtotal" in line.lower():
                try:
                    total = float(line.split()[-1])
                except ValueError:
                    pass
            elif "tax" in line.lower():
                try:
                    tax = float(line.split()[-1])
                except ValueError:
                    pass
            elif any(keyword in line.lower() for keyword in ["/", "-"]):
                date = line.strip()

        return jsonify({
            "message": "Scan successful",
            "raw_text": raw_text,
            "store": store,
            "date": date,
            "total": total,
            "tax": tax
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
