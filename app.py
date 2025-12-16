from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image
import pytesseract
import io
import os
import json
import base64
import re
from dotenv import load_dotenv
from groq import Groq
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}) # Allow all origins for dev

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\yoga\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Configuration
AI_PARSING_ENABLED = os.getenv("AI_PARSING_ENABLED", "true").lower() == "true"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MIN_OCR_CONFIDENCE = float(os.getenv("MIN_OCR_CONFIDENCE", "0.35"))  # Minimum 35% confidence

# Supported categories - frontend will map these to UUIDs
CATEGORIES = [
    "Groceries",
    "Dining",
    "Transport",
    "Entertainment",
    "Shopping",
    "Health",
    "Utilities",
    "Uncategorized"
]

def get_tesseract_confidence(image):
    """Get word-level confidence from Tesseract"""
    # Get detailed OCR data with confidence scores
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    
    # Filter out empty text and calculate average confidence
    confidences = [
        int(conf) for conf, text in zip(data['conf'], data['text']) 
        if int(conf) > 0 and text.strip()
    ]
    
    if not confidences:
        return 0.3
    
    avg_confidence = sum(confidences) / len(confidences) / 100  # Convert to 0-1 scale
    return round(avg_confidence, 2)

def parse_receipt_with_ai(image):
    """Parse receipt using OCR + OpenAI text parsing"""
    # Step 1: OCR the image to get raw text and confidence
    raw_text = pytesseract.image_to_string(image)
    ocr_confidence = get_tesseract_confidence(image)
    
    # Check if OCR confidence is too low
    if ocr_confidence < MIN_OCR_CONFIDENCE:
        raise ValueError(f"OCR confidence too low ({ocr_confidence:.0%}). Image quality insufficient for reliable parsing. Minimum required: {MIN_OCR_CONFIDENCE:.0%}")
    
    # Build category list for the prompt
    category_list = ", ".join(CATEGORIES)
    
    # Step 2: Use Groq to parse the OCR text
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": f"""Receipt parser. Extract data from OCR text. Categories: {category_list}

Rules: Extract readable info only. No fabrication. Use null if unclear. Return {{"error":"unreadable"}} only if complete gibberish. Output JSON only."""
            },
            {
                "role": "user",
                "content": f"""Parse to JSON:
- store: name or null
- date: YYYY-MM-DD or null
- total: amount or null (if missing or 0, sum item totals)
- tax: amount or null
- items: [{{description, quantity (default 1), unitPrice (calc if needed: total/qty), total, category}}]

Price formats: $1.99, 1.99, 1,99. Examples: "2 x $3.50 = $7.00" → qty=2, unit=3.50, total=7.00 | "Milk $4.99" → qty=1, unit=4.99, total=4.99

Text:
{raw_text}"""
            }
        ],
        max_tokens=1500,
        temperature=0.1
    )
    
    # Parse response
    result = response.choices[0].message.content
    # Remove markdown code blocks if present
    if result.startswith("```"):
        result = result.split("```json")[1].split("```")[0].strip() if "```json" in result else result.split("```")[1].split("```")[0].strip()
    
    parsed_data = json.loads(result)
    
    # Check if AI detected unreadable content
    if 'error' in parsed_data and parsed_data['error'] == 'unreadable':
        reason = parsed_data.get('reason', 'Text does not appear to be a valid receipt')
        raise ValueError(f"Receipt text is unreadable or invalid: {reason}")
    
    # Ensure all items have a category
    for item in parsed_data.get('items', []):
        if 'category' not in item or item['category'] not in CATEGORIES:
            item['category'] = 'Uncategorized'
    
    # Add the raw OCR text and confidence
    parsed_data['raw_text'] = raw_text
    parsed_data['ocr_confidence'] = ocr_confidence
    
    return parsed_data

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
        
        # Get real Tesseract confidence score
        ocr_confidence = get_tesseract_confidence(image)

        # Parse structured fields from raw_text
        lines = raw_text.splitlines()
        store = lines[0] if lines else "Unknown Store"
        date = ""
        total = 0.0
        tax = 0.0

        for line in lines:
            if "subtotal" in line.lower() or "total" in line.lower():
                try:
                    # Extract numbers with regex
                    numbers = re.findall(r'\d+\.\d{2}', line)
                    if numbers:
                        total = float(numbers[-1])
                except ValueError:
                    pass
            elif "tax" in line.lower():
                try:
                    numbers = re.findall(r'\d+\.\d{2}', line)
                    if numbers:
                        tax = float(numbers[-1])
                except ValueError:
                    pass
            elif re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line):
                date = line.strip()

        return jsonify({
            "message": "Scan successful",
            "raw_text": raw_text,
            "store": store,
            "date": date,
            "total": total,
            "tax": tax,
            "confidence": ocr_confidence
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/scan-ai", methods=["POST"])
def scan_receipt_ai():
    """AI-powered receipt parsing using OpenAI Vision API"""
    if not AI_PARSING_ENABLED:
        return jsonify({"error": "AI parsing is disabled"}), 503
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if file_ext not in allowed_extensions:
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}), 400
    
    try:
        # Open image directly from upload stream (same as regex endpoint)
        image = Image.open(file.stream)
        
        # Parse with OpenAI (passing image directly, no disk I/O)
        parsed_data = parse_receipt_with_ai(image)
        
        # Use OCR confidence directly
        parsed_data['confidence'] = parsed_data.get('ocr_confidence', 0.7)
        
        # Generate unique IDs for items if not present
        for i, item in enumerate(parsed_data.get('items', [])):
            if 'id' not in item:
                item['id'] = f"item-{i+1}"
        
        return jsonify(parsed_data), 200
    
    except ValueError as e:
        # Handle low confidence or unreadable content
        error_msg = str(e)
        return jsonify({
            'error': 'Unable to parse receipt',
            'reason': error_msg,
            'suggestion': 'Please upload a clearer image with better lighting and focus'
        }), 400
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON response from AI: {str(e)}'}), 500
    except Exception as e:
        print(f"Error in AI parsing: {str(e)}")
        return jsonify({'error': f'AI parsing failed: {str(e)}'}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
