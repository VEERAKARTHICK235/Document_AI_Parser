import os, re, io, requests
import numpy as np
import pandas as pd
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import cv2
from dotenv import load_dotenv


load_dotenv()
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Poppler\poppler-23.11.0\Library\bin"


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
)

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key not found."
    try:
        r = requests.post(
            GEMINI_URL,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Gemini Error: {e}"

# Image pre‑processing
def preprocess(img: Image.Image) -> Image.Image:
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
    )
    return Image.fromarray(thresh)

# Main parser 
def process_file(uploaded):
    # Load first page / image
    pil = (
        convert_from_bytes(uploaded.read(), poppler_path=POPPLER_PATH)[0]
        if uploaded.type == "application/pdf"
        else Image.open(uploaded)
    )

    # OCR
    text = pytesseract.image_to_string(preprocess(pil))

    # Extract items
    rows = []
    skip = re.compile(r"(invoice|date|gst|state|city|total|tax|amount|vendor|balance|code)", re.I)
    pattern = re.compile(
        r"(?:(\d+)\s*[x×*]?\s*)?([A-Za-z][A-Za-z0-9\s\-&]*)\s+([₹$]?\d+[.,]?\d*)",
        re.I,
    )

    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue

        # Keep if pattern matches, else skip obvious headers
        if skip.search(ln) and not pattern.search(ln):
            continue

        m = pattern.search(ln)
        if not m:
            continue

        qty = int(m.group(1)) if m.group(1) else 1
        name = m.group(2).strip()
        price = float(m.group(3).lstrip("₹$").replace(",", ""))

        # Filter noise
        if (
            len(name) < 3
            or name.lower() in {"%", "-", "x", "state", "total", "invoice", "amount", "code"}
            or re.fullmatch(r"[A-Z0-9]{4,}", name)  
            or (name.isupper() and name.isalpha() and len(name) > 3)
        ):
            continue

        rows.append({
            "Product Name": name,
            "Quantity": qty,
            "Unit Price": price,
            "Net Amount": round(qty * price, 2),
        })

    if not rows:
        rows.append({
            "Product Name": "No items detected",
            "Quantity": 0,
            "Unit Price": 0.0,
            "Net Amount": 0.0,
        })

    # DataFrame + Grand Total 
    df = pd.DataFrame(rows)
    grand_total = df["Net Amount"].sum()
    df.loc[len(df.index)] = {
        "Product Name": "Grand Total",
        "Quantity": pd.NA,
        "Unit Price": pd.NA,
        "Net Amount": round(grand_total, 2),
    }

    # Excel export
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Line_Items")
    excel_bytes = buf.getvalue()

    # AI Summary
    summary = call_gemini(f"Summarize this invoice:\n{text}")

    return {
        "summary": summary,
        "AI_Table": df,
        "excel_bytes": excel_bytes,
    }
