import os, re, io, requests, platform
import numpy as np
import pandas as pd
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import cv2
from dotenv import load_dotenv
from pathlib import Path

# ── Load environment variables ───────────────────────────
load_dotenv()

# ── Setup Tesseract command ──────────────────────────────
TESSERACT_CMD = os.getenv("TESSERACT_CMD")
if not TESSERACT_CMD:
    if platform.system() == "Windows":
        TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    else:
        TESSERACT_CMD = "/usr/bin/tesseract"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ── Setup Poppler path ───────────────────────────────────
POPPLER_PATH = os.getenv("POPPLER_PATH")
if not POPPLER_PATH:
    if platform.system() == "Windows":
        POPPLER_PATH = r"C:\Poppler\poppler-23.11.0\Library\bin"
    else:
        POPPLER_PATH = "/usr/bin"

# ── Gemini API Setup ─────────────────────────────────────
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

# ── Image Preprocessing ──────────────────────────────────
def preprocess(img: Image.Image) -> Image.Image:
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
    )
    return Image.fromarray(thresh)

# ── Main OCR + NLP Parser ────────────────────────────────
def process_file(uploaded):
    # 1. Read page/image
    pil = (
        convert_from_bytes(uploaded.read(), poppler_path=POPPLER_PATH)[0]
        if uploaded.type == "application/pdf"
        else Image.open(uploaded)
    )

    # 2. OCR
    text = pytesseract.image_to_string(preprocess(pil))

    # 3. Regex Parse
    rows = []
    skip = re.compile(r"(invoice|date|gst|state|city|total|tax|amount|vendor|balance|code)", re.I)
    pattern = re.compile(
        r"(?:(\d+)\s*[x×*]?\s*)?([A-Za-z][A-Za-z0-9\s\-&]*)\s+([₹$]?\d+[.,]?\d*)",
        re.I,
    )

    for line in text.splitlines():
        ln = line.strip()
        if not ln:
            continue
        if skip.search(ln) and not pattern.search(ln):
            continue

        match = pattern.search(ln)
        if not match:
            continue

        qty = int(match.group(1)) if match.group(1) else 1
        name = match.group(2).strip()
        price = float(match.group(3).lstrip("₹$").replace(",", ""))

        # Clean noise
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

    # 4. DataFrame & Grand Total
    df = pd.DataFrame(rows)
    total = df["Net Amount"].sum()
    df.loc[len(df.index)] = {
        "Product Name": "Grand Total",
        "Quantity": pd.NA,
        "Unit Price": pd.NA,
        "Net Amount": round(total, 2),
    }

    # 5. Excel export
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Line_Items")
    excel_bytes = buf.getvalue()

    # 6. Gemini summary
    summary = call_gemini(f"Summarize this invoice:\n{text}")

    return {
        "summary": summary,
        "AI_Table": df,
        "excel_bytes": excel_bytes,
    }
