# Receipt Scanner Backend API Documentation

## Overview

This Flask-based backend provides receipt scanning and parsing capabilities using OCR (Optical Character Recognition) and AI-powered text analysis. The system offers two parsing modes: regex-based extraction with optional AI categorization, and full AI-powered parsing.

**Technology Stack:**
- **Framework:** Flask 3.0.0 (Python web framework)
- **OCR Engine:** PaddleOCR (deep learning-based OCR with bounding box detection)
- **AI Provider:** Groq API (LLaMA 3.3 70B Versatile model)
- **Image Processing:** Pillow (PIL), NumPy
- **CORS:** Flask-CORS (enabled for all origins in development)

---

## Configuration

### Environment Variables

The application uses `.env` file for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | Required | API key for Groq AI service |
| `AI_PARSING_ENABLED` | `"true"` | Enable/disable AI features |
| `GROQ_MODEL` | `"llama-3.3-70b-versatile"` | Groq AI model to use |
| `MIN_OCR_CONFIDENCE` | `0.35` | Minimum OCR confidence threshold (35%) |

### PaddleOCR Configuration

The application uses PaddleOCR for text extraction with the following settings:
- **Language:** English (`lang='en'`)
- **Angle Classification:** Enabled (`use_angle_cls=True`) - handles rotated text
- **Show Logs:** Disabled for cleaner output

**No installation required** - PaddleOCR is automatically installed via pip and downloads models on first use.

### Supported Categories

Items are categorized into predefined categories:
- **Groceries**
- **Dining**
- **Transport**
- **Entertainment**
- **Shopping**
- **Health**
- **Utilities**
- **Uncategorized** (fallback)

---

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /api/health`

**Description:** Simple health check to verify the service is running.

**Response:**
```json
{
  "status": "ok"
}
```

---

### 2. Regex-Based Receipt Scan

**Endpoint:** `POST /api/scan`

**Description:** Scans receipt images using OCR and regex pattern matching to extract structured data. Optionally uses AI to categorize extracted items.

**Request:**
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Body:** 
  - `file`: Image file (receipt photo)

**Process Flow:**
1. **OCR Extraction:** Extracts raw text and bounding boxes from the image using PaddleOCR
2. **Confidence Check:** Calculates OCR confidence score
3. **Regex Parsing:** Uses pattern matching to extract:
   - Store name (first line)
   - Date (DD/MM/YYYY or MM-DD-YYYY format)
   - Total amount (lines containing "total" or "subtotal")
   - Tax amount (lines containing "tax")
   - Individual items with prices
4. **Item Extraction:** Identifies items using regex patterns:
   - Matches lines ending with prices (e.g., "Milk $4.99" or "Bread 3.50")
   - Detects quantity patterns (e.g., "2 x Milk $9.98")
   - Calculates unit prices from quantities
   - Filters out non-item lines (totals, tax, etc.)
5. **AI Categorization (Conditional):** 
   - **Only if items are extracted** AND AI is enabled
   - Sends item descriptions to Groq AI for category classification
   - Falls back to "Uncategorized" if AI fails or is disabled

**Regex Patterns Used:**
- **Price extraction:** `\d+\.\d{2}` - Matches decimal prices (e.g., 4.99)
- **Date detection:** `\d{1,2}[/-]\d{1,2}[/-]\d{2,4}` - Matches date formats
- **Item parsing:** `(.*?)\s*[\$]?\s*(\d+[.,]\d{2})$` - Matches description + price
- **Quantity detection:** `(\d+)\s*x\s*(.*)` - Matches "2 x Item" patterns

**Success Response (200):**
```json
{
  "message": "Scan successful",
  "raw_text": "OCR extracted text...",
  "store": "Store Name",
  "date": "12/16/2025",
  "total": 42.50,
  "tax": 3.40,
  "items": [
    {
      "description": "Milk",
      "quantity": 2,
      "unitPrice": 2.49,
      "total": 4.98,
      "category": "Groceries"
    }
  ],
  "confidence": 0.85,
  "ocr_data": [
    {
      "text": "Store Name",
      "confidence": 0.982,
      "bounding_box": {
        "top_left": [45, 120],
        "top_right": [210, 120],
        "bottom_right": [210, 145],
        "bottom_left": [45, 145]
      }
    },
    {
      "text": "Milk $4.98",
      "confidence": 0.875,
      "bounding_box": {
        "top_left": [45, 220],
        "top_right": [185, 220],
        "bottom_right": [185, 242],
        "bottom_left": [45, 242]
      }
    }
  ]
}
```

**OCR Data Structure:**
Each element in the `ocr_data` array contains:
- `text`: The detected text string
- `confidence`: Confidence score (0-1, rounded to 3 decimals)
- `bounding_box`: Object with 4 corner coordinates (in pixels):
  - `top_left`: [x, y] - Top-left corner
  - `top_right`: [x, y] - Top-right corner
  - `bottom_right`: [x, y] - Bottom-right corner
  - `bottom_left`: [x, y] - Bottom-left corner

**Error Response (400/500):**
```json
{
  "error": "Error message"
}
```

**Key Features:**
- ✅ Fast processing (no AI overhead for basic extraction)
- ✅ Works without AI if disabled
- ✅ Real-time confidence scoring
- ✅ Smart quantity detection
- ✅ AI categorization only when items are found

---

### 3. AI-Powered Receipt Scan

**Endpoint:** `POST /api/scan-ai`

**Description:** Comprehensive AI-powered receipt parsing that uses OCR + Groq AI for intelligent data extraction and categorization.

**Request:**
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Body:** 
  - `file`: Image file (receipt photo)

**Supported File Types:**
- PNG, JPG, JPEG, GIF, BMP, WEBP

**Process Flow:**
1. **File Validation:** Checks file type against allowed extensions
2. **OCR Extraction:** Extracts text and bounding boxes using PaddleOCR
3. **Confidence Check:** Validates OCR confidence meets minimum threshold (35%)
4. **AI Parsing:** Sends OCR text to Groq AI with structured prompts:
   - Extract store name
   - Parse date (YYYY-MM-DD format)
   - Identify total amount
   - Extract tax
   - Parse individual items with descriptions, quantities, prices, and categories
5. **Response Validation:** Ensures all items have valid categories
6. **ID Generation:** Assigns unique IDs to each item

**AI Prompt Strategy:**
- **System Role:** Receipt parser with strict extraction rules
- **Temperature:** 0.1 (low randomness for consistent results)
- **Max Tokens:** 1500
- **Instructions:** Extract only readable info, no fabrication, null for unclear fields

**Success Response (200):**
```json
{
  "store": "Walmart",
  "date": "2025-12-16",
  "total": 42.50,
  "tax": 3.40,
  "items": [
    {
      "id": "item-1",
      "description": "Organic Milk 2%",
      "quantity": 2,
      "unitPrice": 2.49,
      "total": 4.98,
      "category": "Groceries"
    },
    {
      "id": "item-2",
      "description": "Bread Whole Wheat",
      "quantity": 1,
      "unitPrice": 3.99,
      "total": 3.99,
      "category": "Groceries"
    }
  ],
  "raw_text": "Full OCR text...",
  "ocr_confidence": 0.85,
  "confidence": 0.85,
  "ocr_data": [
    {
      "text": "Walmart",
      "confidence": 0.991,
      "bounding_box": {
        "top_left": [125, 80],
        "top_right": [285, 80],
        "bottom_right": [285, 115],
        "bottom_left": [125, 115]
      }
    },
    {
      "text": "2025-12-16",
      "confidence": 0.943,
      "bounding_box": {
        "top_left": [50, 130],
        "top_right": [180, 130],
        "bottom_right": [180, 150],
        "bottom_left": [50, 150]
      }
    }
  ]
}
```

**Error Responses:**

**AI Parsing Disabled (503):**
```json
{
  "error": "AI parsing is disabled"
}
```

**Low OCR Confidence (400):**
```json
{
  "error": "Unable to parse receipt",
  "reason": "OCR confidence too low (25%). Image quality insufficient...",
  "suggestion": "Please upload a clearer image with better lighting and focus"
}
```

**Invalid File Type (400):**
```json
{
  "error": "Invalid file type. Allowed: png, jpg, jpeg, gif, bmp, webp"
}
```

**AI Parsing Failure (500):**
```json
{
  "error": "AI parsing failed: <error details>"
}
```

---

## Core Functions

### `perform_ocr_with_paddleocr(image)`

**Purpose:** Performs OCR using PaddleOCR and returns text, confidence scores, and bounding boxes for each detected text region.

**Process:**
1. Converts PIL Image to NumPy array for PaddleOCR compatibility
2. Runs PaddleOCR with angle classification enabled
3. Extracts text lines, confidence scores, and bounding box coordinates
4. Formats bounding boxes as 4-corner coordinates (top-left, top-right, bottom-right, bottom-left)
5. Calculates average confidence across all detected text regions
6. Returns tuple: (full_text, avg_confidence, ocr_data)

**Returns:**
- `full_text` (str): All detected text joined by newlines
- `avg_confidence` (float): Average confidence score (0-1, rounded to 3 decimals)
- `ocr_data` (list): Array of objects containing:
  - `text`: Detected text string
  - `confidence`: Individual confidence score
  - `bounding_box`: Dictionary with 4 corner coordinates

**Advantages over Tesseract:**
- ✅ Better accuracy with handwritten and low-quality images
- ✅ Native bounding box detection (no additional processing needed)
- ✅ Handles rotated and skewed text automatically
- ✅ Deep learning-based (more robust to various fonts and layouts)
- ✅ No external installation required (pure Python)

---

### `get_tesseract_confidence(image)`

**[DEPRECATED - Replaced by `perform_ocr_with_paddleocr`]**

**Purpose:** Calculates the average OCR confidence score for an image.

**Process:**
1. Runs Tesseract OCR with detailed output (word-level confidence)
2. Filters out empty text and invalid confidence scores
3. Calculates average confidence across all detected words
4. Converts from 0-100 scale to 0-1 scale
5. Returns 0.3 if no valid confidence scores found

**Returns:** Float between 0.0 and 1.0

**Usage:** Quality assurance before parsing receipts

---

### `categorize_items_with_ai(items)`

**Purpose:** Uses AI to categorize extracted items from regex parsing.

**Input:** List of items with descriptions

**Process:**
1. Checks if items list is empty (returns immediately if so)
2. Formats items as numbered list
3. Sends to Groq AI with categorization prompt
4. Parses JSON array response
5. Assigns categories to items in order
6. Falls back to "Uncategorized" for invalid categories

**Returns:** List of items with `category` field added

**AI Model:** LLaMA 3.3 70B Versatile
**Temperature:** 0.1 (deterministic categorization)
**Max Tokens:** 500

**Example AI Response:**
```json
["Groceries", "Groceries", "Dining", "Transport"]
```

---

### `parse_receipt_with_ai(image)`

**Purpose:** Full AI-powered receipt parsing (used by `/api/scan-ai`)

**Input:** PIL Image object

**Process:**
1. **OCR Stage:**
   - Extract text using Tesseract
   - Calculate confidence score
   - Reject if confidence < 35%

2. **AI Parsing Stage:**
   - Send OCR text to Groq AI
   - Request structured JSON with store, date, total, tax, items
   - AI validates and categorizes items
   - Handles price formats: $1.99, 1.99, 1,99
   - Calculates unit prices from quantities

3. **Validation Stage:**
   - Check for "unreadable" error flag
   - Validate categories
   - Set defaults (Uncategorized) for invalid categories

4. **Response Formatting:**
   - Add raw OCR text
   - Add confidence score
   - Return complete structured data

**Error Handling:**
- Raises `ValueError` for low confidence
- Raises `ValueError` for unreadable receipts
- Parses markdown code blocks from AI responses

---

## Comparison: `/api/scan` vs `/api/scan-ai`

| Feature | `/api/scan` (Regex) | `/api/scan-ai` (Full AI) |
|---------|---------------------|--------------------------|
| **Speed** | ⚡ Fast | 🐢 Slower (AI call required) |
| **Accuracy** | ✅ Good for standard formats | ✅✅ Excellent for complex formats |
| **Item Extraction** | Regex pattern matching | AI understanding |
| **Categorization** | Optional AI (only if items found) | Always included |
| **AI Dependency** | Optional | Required |
| **Best For** | Simple, well-formatted receipts | Complex, varied receipt formats |
| **Offline Mode** | ✅ Partial (no categories) | ❌ Requires AI |
| **Cost** | 💰 Low (1 AI call if items exist) | 💰💰 Higher (always uses AI) |

---

## Error Handling

### OCR Confidence Threshold

The system rejects images with OCR confidence below 35% to prevent unreliable parsing:

```python
if ocr_confidence < MIN_OCR_CONFIDENCE:
    raise ValueError("OCR confidence too low...")
```

**Common Causes:**
- Blurry images
- Poor lighting
- Low resolution
- Skewed/rotated receipts
- Faded text

### AI Categorization Fallback

If AI categorization fails in `/api/scan`, items are automatically set to "Uncategorized":

```python
except Exception as e:
    print(f"AI categorization failed: {str(e)}")
    for item in items:
        item['category'] = 'Uncategorized'
```

### Markdown Code Block Handling

AI responses may be wrapped in markdown. The system automatically strips these:

```python
if result.startswith("```"):
    result = result.split("```json")[1].split("```")[0].strip()
```

---

## Security Considerations

### CORS Configuration

⚠️ **Development Mode:** CORS is currently set to allow all origins:

```python
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

**Production Recommendation:** Restrict to specific origins:

```python
CORS(app, resources={r"/api/*": {"origins": ["https://yourdomain.com"]}})
```

### File Upload Validation

- ✅ File type validation (whitelist approach)
- ✅ Secure filename handling (werkzeug.secure_filename available)
- ⚠️ No file size limits currently enforced
- ⚠️ No rate limiting

**Recommended Additions:**
- Maximum file size limit (e.g., 10MB)
- Rate limiting per IP
- File content validation (verify actual file type)

---

## Running the Application

### Development Mode

```bash
python app.py
```

- Server runs on `http://localhost:5000`
- Debug mode enabled
- Auto-reload on code changes

### Production Recommendations

Use a production WSGI server (Gunicorn, uWSGI):

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## Dependencies

```
Flask==3.0.0           # Web framework
flask-cors==4.0.0      # CORS support
Pillow==10.1.0         # Image processing
pytesseract==0.3.10    # OCR wrapper
groq                   # Groq AI API client
python-dotenv          # Environment variables
```

**External Requirements:**
- Tesseract OCR (system installation required)
- Groq API account and API key

---

## Response Time Analysis

### `/api/scan` (Regex Mode)

1. OCR Extraction: ~1-3 seconds
2. Regex Parsing: <100ms
3. AI Categorization (if items): ~1-2 seconds
4. **Total: 1-5 seconds**

### `/api/scan-ai` (Full AI Mode)

1. OCR Extraction: ~1-3 seconds
2. AI Parsing: ~2-4 seconds
3. **Total: 3-7 seconds**

**Optimization Tips:**
- Use `/api/scan` for real-time scanning
- Use `/api/scan-ai` for best accuracy
- Implement caching for repeated requests
- Consider image preprocessing (resize, enhance) before OCR

---

## Future Enhancements

### Potential Improvements

1. **Receipt Preprocessing:**
   - Image rotation correction
   - Contrast enhancement
   - Noise reduction
   - Perspective correction

2. **Parsing Enhancements:**
   - Multi-language support
   - Currency conversion
   - Store-specific parsers
   - Discount/coupon detection

3. **Performance:**
   - Redis caching for repeated uploads
   - Async processing with Celery
   - WebSocket for real-time progress
   - Batch processing endpoint

4. **Security:**
   - Rate limiting (Flask-Limiter)
   - File size limits
   - Image validation (actual format check)
   - API authentication

5. **Monitoring:**
   - Logging framework
   - Error tracking (Sentry)
   - Performance metrics
   - OCR confidence analytics

---

## Troubleshooting

### "OCR confidence too low" Error

**Solution:**
- Ensure good lighting when photographing receipts
- Hold camera steady (avoid blur)
- Capture receipt straight-on (not at an angle)
- Use higher resolution images
- Clean the receipt (remove crumples)

### AI Categorization Not Working

**Check:**
1. `AI_PARSING_ENABLED` is set to `"true"` in `.env`
2. `GROQ_API_KEY` is valid and not expired
3. Items were actually extracted by regex
4. Network connectivity to Groq API

### Tesseract Not Found

**Solution:**
1. Install Tesseract OCR
2. Update `pytesseract.pytesseract.tesseract_cmd` path
3. Add Tesseract to system PATH

### Items Not Being Extracted

**Common Issues:**
- Receipt format doesn't match regex patterns
- Prices not in standard format (X.XX)
- OCR misread prices or descriptions
- **Solution:** Use `/api/scan-ai` for complex formats

---

## API Usage Examples

### Python Request Example

```python
import requests

# Regex scan
with open('receipt.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/scan',
        files={'file': f}
    )
    print(response.json())

# AI scan
with open('receipt.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/scan-ai',
        files={'file': f}
    )
    print(response.json())
```

### cURL Example

```bash
# Regex scan
curl -X POST http://localhost:5000/api/scan \
  -F "file=@receipt.jpg"

# AI scan
curl -X POST http://localhost:5000/api/scan-ai \
  -F "file=@receipt.jpg"
```

### JavaScript (Fetch API)

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

// Regex scan
const response = await fetch('http://localhost:5000/api/scan', {
  method: 'POST',
  body: formData
});
const data = await response.json();
console.log(data);
```

---

## License & Credits

**OCR Engine:** Tesseract OCR (Apache 2.0)
**AI Provider:** Groq (LLaMA 3.3 by Meta)
**Framework:** Flask (BSD-3-Clause)

---

**Last Updated:** December 16, 2025
**Version:** 1.0
**Author:** Backend Development Team
