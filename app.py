import streamlit as st
from dotenv import load_dotenv


load_dotenv()

from utils.parser import process_file  

st.set_page_config(page_title="Document AI Parser (Tesseract + AI)", layout="centered")

st.title("📄 Document AI Parser")
st.markdown(
    "Upload an invoice / receipt **(PDF | PNG | JPG)**. "
    "The app extracts line‑items (with Quantity, Unit Price, Net Amount) "
    "and shows a AI summary plus an Excel download."
)

uploaded = st.file_uploader("Upload File", type=["pdf", "png", "jpg", "jpeg"])

if uploaded:
    st.success(f"✅ Uploaded: {uploaded.name}")
    with st.spinner("🔎 Parsing with OCR + AI"):
        try:
            result = process_file(uploaded)

            st.subheader("🧠 AI Summary")
            st.markdown(result["summary"], unsafe_allow_html=True)

            st.subheader("📊 Line Items")
            st.dataframe(result["AI_Table"], use_container_width=True)

            st.download_button(
                "⬇️ Download Excel",
                data=result["excel_bytes"],
                file_name="invoice_items.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as err:
            st.error(f"❌ Parsing failed: {err}")
