# 🧾 Document AI — Invoice & Receipt Parser (Tesseract + AI)

This project is a smart Document AI tool built with **Streamlit**, combining the power of **Tesseract OCR** and **AI** to extract and summarize data from invoices and receipts.

---

## 🚀 Features

✅ Extracts:
- Product Name  
- Quantity  
- Unit Price  
- Net Amount  
- Grand Total  

✨ AI-Powered:
- Uses Google AI to generate natural-language summaries.
- Smart fallback for missing invoice metadata (vendor, date, total, tax).

📎 Supported Formats:
- PDF, JPG, PNG, JPEG invoices or receipts.

📤 Outputs:
- Downloadable Excel sheet of all line-items.
- AI generated invoice summary.

---

## 🧠 Technologies Used

- **Python** (3.8+)
- **Streamlit** – Web UI
- **Tesseract OCR** – Optical character recognition
- **Google API** – LLM-based text understanding
- **OpenCV** – Image preprocessing
- **pdf2image** – PDF to image conversion
- **pandas** – Data manipulation and export
- **dotenv** – Secure API key management

---

## Install Tesseract OCR & Poppler

🟩 Tesseract OCR
Install and update the pytesseract.pytesseract.tesseract_cmd path in parser.py.

🟦 Poppler
Required for PDF to image conversion. Add its /bin path to POPPLER_PATH.

---

## Run the app

streamlit run app.py







