# Frontend Integration Guide - PaddleOCR Bounding Boxes

## Overview

The backend now uses **PaddleOCR** instead of Tesseract. Both endpoints (`/api/scan` and `/api/scan-ai`) return bounding box coordinates for all detected text, which you can use to draw boxes on the receipt image in the frontend.

---

## What Changed

### ✅ NEW: Bounding Box Data
Both endpoints now return an `ocr_data` array containing:
- Detected text
- Confidence scores
- **Bounding box coordinates** for each text region

### ✅ Improved Accuracy
PaddleOCR provides better text detection, especially for:
- Low-quality images
- Rotated or skewed receipts
- Various fonts and handwriting

---

## API Response Structure

### 1. `/api/scan` Endpoint (Regex-based)

**Response includes new `ocr_data` field:**

```json
{
  "message": "Scan successful",
  "raw_text": "Store Name\n12/16/2025\nMilk $4.98\nBread $3.99\nTotal $8.97",
  "store": "Store Name",
  "date": "12/16/2025",
  "total": 8.97,
  "tax": 0.0,
  "items": [...],
  "confidence": 0.875,
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
      "confidence": 0.891,
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

---

### 2. `/api/scan-ai` Endpoint (AI-powered)

**Same `ocr_data` structure:**

```json
{
  "store": "Walmart",
  "date": "2025-12-16",
  "total": 42.50,
  "tax": 3.40,
  "items": [...],
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
    }
  ]
}
```

---

## Bounding Box Data Structure

Each element in `ocr_data` array:

```typescript
interface OcrData {
  text: string;              // Detected text
  confidence: number;        // 0-1 (e.g., 0.982 = 98.2%)
  bounding_box: {
    top_left: [number, number];      // [x, y]
    top_right: [number, number];     // [x, y]
    bottom_right: [number, number];  // [x, y]
    bottom_left: [number, number];   // [x, y]
  };
}
```

### Coordinate System
- **Origin (0,0):** Top-left corner of the image
- **X-axis:** Increases to the right
- **Y-axis:** Increases downward
- **Units:** Pixels relative to original image dimensions

---

## Frontend Implementation

### 1. Basic HTML5 Canvas Example

```javascript
function drawBoundingBoxes(imageElement, ocrData) {
  const canvas = document.getElementById('receipt-canvas');
  const ctx = canvas.getContext('2d');
  
  // Set canvas size to match image
  canvas.width = imageElement.naturalWidth;
  canvas.height = imageElement.naturalHeight;
  
  // Draw the receipt image
  ctx.drawImage(imageElement, 0, 0);
  
  // Draw bounding boxes
  ocrData.forEach((item) => {
    const box = item.bounding_box;
    
    // Start drawing path
    ctx.beginPath();
    ctx.moveTo(box.top_left[0], box.top_left[1]);
    ctx.lineTo(box.top_right[0], box.top_right[1]);
    ctx.lineTo(box.bottom_right[0], box.bottom_right[1]);
    ctx.lineTo(box.bottom_left[0], box.bottom_left[1]);
    ctx.closePath();
    
    // Style the box
    ctx.strokeStyle = 'rgba(255, 0, 0, 0.8)';  // Red with transparency
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Optional: Add confidence label
    ctx.fillStyle = 'rgba(255, 0, 0, 0.8)';
    ctx.font = '12px Arial';
    ctx.fillText(
      `${(item.confidence * 100).toFixed(1)}%`, 
      box.top_left[0], 
      box.top_left[1] - 5
    );
  });
}

// Usage after API response
fetch('/api/scan', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  const img = document.getElementById('receipt-image');
  img.onload = () => {
    drawBoundingBoxes(img, data.ocr_data);
  };
  img.src = URL.createObjectURL(uploadedFile);
});
```

---

### 2. React Example with TypeScript

```typescript
interface BoundingBox {
  top_left: [number, number];
  top_right: [number, number];
  bottom_right: [number, number];
  bottom_left: [number, number];
}

interface OcrData {
  text: string;
  confidence: number;
  bounding_box: BoundingBox;
}

interface ScanResponse {
  message: string;
  raw_text: string;
  store: string;
  date: string;
  total: number;
  tax: number;
  items: any[];
  confidence: number;
  ocr_data: OcrData[];
}

const ReceiptViewer: React.FC<{ scanResult: ScanResponse }> = ({ scanResult }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !imageRef.current || !scanResult.ocr_data) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = imageRef.current;

    if (!ctx) return;

    // Wait for image to load
    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;

      // Draw image
      ctx.drawImage(img, 0, 0);

      // Draw bounding boxes
      scanResult.ocr_data.forEach((item) => {
        const box = item.bounding_box;

        ctx.beginPath();
        ctx.moveTo(box.top_left[0], box.top_left[1]);
        ctx.lineTo(box.top_right[0], box.top_right[1]);
        ctx.lineTo(box.bottom_right[0], box.bottom_right[1]);
        ctx.lineTo(box.bottom_left[0], box.bottom_left[1]);
        ctx.closePath();

        // Color code by confidence
        const color = item.confidence > 0.9 ? 'green' : 
                     item.confidence > 0.7 ? 'orange' : 'red';
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Add text label
        ctx.fillStyle = color;
        ctx.font = '12px Arial';
        ctx.fillText(
          `${item.text} (${(item.confidence * 100).toFixed(0)}%)`,
          box.top_left[0],
          box.top_left[1] - 5
        );
      });
    };
  }, [scanResult]);

  return (
    <div>
      <img ref={imageRef} src={scanResult.imageUrl} style={{ display: 'none' }} />
      <canvas ref={canvasRef} />
    </div>
  );
};
```

---

### 3. SVG Overlay Example

```javascript
function createSvgOverlay(imageElement, ocrData) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', imageElement.naturalWidth);
  svg.setAttribute('height', imageElement.naturalHeight);
  svg.style.position = 'absolute';
  svg.style.top = '0';
  svg.style.left = '0';
  svg.style.pointerEvents = 'none';

  ocrData.forEach((item) => {
    const box = item.bounding_box;
    
    // Create polygon for bounding box
    const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    const points = `
      ${box.top_left[0]},${box.top_left[1]}
      ${box.top_right[0]},${box.top_right[1]}
      ${box.bottom_right[0]},${box.bottom_right[1]}
      ${box.bottom_left[0]},${box.bottom_left[1]}
    `;
    
    polygon.setAttribute('points', points.trim());
    polygon.setAttribute('fill', 'none');
    polygon.setAttribute('stroke', 'red');
    polygon.setAttribute('stroke-width', '2');
    
    svg.appendChild(polygon);
  });

  return svg;
}
```

---

## Advanced Features

### 1. Interactive Bounding Boxes

```javascript
function drawInteractiveBoundingBoxes(imageElement, ocrData) {
  const canvas = document.getElementById('receipt-canvas');
  const ctx = canvas.getContext('2d');
  
  canvas.width = imageElement.naturalWidth;
  canvas.height = imageElement.naturalHeight;
  ctx.drawImage(imageElement, 0, 0);
  
  let hoveredIndex = -1;
  
  // Draw function
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(imageElement, 0, 0);
    
    ocrData.forEach((item, index) => {
      const box = item.bounding_box;
      const isHovered = index === hoveredIndex;
      
      ctx.beginPath();
      ctx.moveTo(box.top_left[0], box.top_left[1]);
      ctx.lineTo(box.top_right[0], box.top_right[1]);
      ctx.lineTo(box.bottom_right[0], box.bottom_right[1]);
      ctx.lineTo(box.bottom_left[0], box.bottom_left[1]);
      ctx.closePath();
      
      // Highlight hovered box
      ctx.strokeStyle = isHovered ? 'yellow' : 'red';
      ctx.lineWidth = isHovered ? 3 : 2;
      ctx.stroke();
      
      // Fill hovered box with semi-transparent color
      if (isHovered) {
        ctx.fillStyle = 'rgba(255, 255, 0, 0.2)';
        ctx.fill();
        
        // Show tooltip
        ctx.fillStyle = 'black';
        ctx.font = 'bold 14px Arial';
        ctx.fillText(
          `"${item.text}" - ${(item.confidence * 100).toFixed(1)}%`,
          box.top_left[0],
          box.top_left[1] - 10
        );
      }
    });
  }
  
  // Mouse move handler
  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    
    // Check if mouse is inside any bounding box
    hoveredIndex = ocrData.findIndex((item) => {
      const box = item.bounding_box;
      return isPointInPolygon([x, y], [
        box.top_left,
        box.top_right,
        box.bottom_right,
        box.bottom_left
      ]);
    });
    
    draw();
  });
  
  draw();
}

// Helper function to check if point is inside polygon
function isPointInPolygon(point, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0], yi = polygon[i][1];
    const xj = polygon[j][0], yj = polygon[j][1];
    
    const intersect = ((yi > point[1]) !== (yj > point[1]))
      && (point[0] < (xj - xi) * (point[1] - yi) / (yj - yi) + xi);
    
    if (intersect) inside = !inside;
  }
  return inside;
}
```

---

### 2. Filter by Confidence

```javascript
function drawHighConfidenceOnly(imageElement, ocrData, minConfidence = 0.8) {
  const filteredData = ocrData.filter(item => item.confidence >= minConfidence);
  drawBoundingBoxes(imageElement, filteredData);
}
```

---

### 3. Color-Coded by Confidence

```javascript
function getConfidenceColor(confidence) {
  if (confidence >= 0.9) return 'rgba(0, 255, 0, 0.8)';   // Green - high
  if (confidence >= 0.7) return 'rgba(255, 165, 0, 0.8)'; // Orange - medium
  return 'rgba(255, 0, 0, 0.8)';                          // Red - low
}

function drawColorCodedBoundingBoxes(imageElement, ocrData) {
  const canvas = document.getElementById('receipt-canvas');
  const ctx = canvas.getContext('2d');
  
  canvas.width = imageElement.naturalWidth;
  canvas.height = imageElement.naturalHeight;
  ctx.drawImage(imageElement, 0, 0);
  
  ocrData.forEach((item) => {
    const box = item.bounding_box;
    
    ctx.beginPath();
    ctx.moveTo(box.top_left[0], box.top_left[1]);
    ctx.lineTo(box.top_right[0], box.top_right[1]);
    ctx.lineTo(box.bottom_right[0], box.bottom_right[1]);
    ctx.lineTo(box.bottom_left[0], box.bottom_left[1]);
    ctx.closePath();
    
    ctx.strokeStyle = getConfidenceColor(item.confidence);
    ctx.lineWidth = 2;
    ctx.stroke();
  });
}
```

---

## Testing

### Sample cURL Request

```bash
curl -X POST http://localhost:5000/api/scan \
  -F "file=@receipt.jpg"
```

### Expected Response

```json
{
  "message": "Scan successful",
  "ocr_data": [
    {
      "text": "WALMART",
      "confidence": 0.991,
      "bounding_box": {
        "top_left": [120, 50],
        "top_right": [280, 50],
        "bottom_right": [280, 85],
        "bottom_left": [120, 85]
      }
    }
  ],
  ...
}
```

---

## Key Points for Frontend Dev

1. **Both endpoints** (`/api/scan` and `/api/scan-ai`) now include `ocr_data`
2. **Coordinates are in pixels** relative to the original image dimensions
3. **Bounding boxes are 4-point polygons** (not rectangles) - can be rotated
4. **Confidence scores** range from 0 to 1 (multiply by 100 for percentage)
5. **Draw after image loads** - ensure image dimensions are available
6. **Scale coordinates** if displaying image at different size than original

---

## Performance Tips

- **Canvas is faster** for static displays
- **SVG is better** for interactive features (hover, click)
- **Cache the drawing** - don't redraw on every mousemove
- **Use requestAnimationFrame** for smooth animations
- **Debounce interactions** to avoid excessive redraws

---

## Migration Checklist

- [ ] Update API response TypeScript interfaces to include `ocr_data`
- [ ] Implement bounding box drawing function
- [ ] Test with various image sizes and qualities
- [ ] Add confidence-based color coding (optional)
- [ ] Implement interactive features (optional)
- [ ] Add loading states during OCR processing
- [ ] Handle cases where `ocr_data` might be empty

---

## Questions?

Check [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API reference.
