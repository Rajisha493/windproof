import streamlit as st
import pdfplumber
from difflib import unified_diff

st.set_page_config(page_title="WindProof - PDF Comparator", layout="wide")
st.title("🌬️ WindProof - PDF Comparison Tool")

def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def compare_texts(text1, text2):
    diff = list(unified_diff(
        text1.splitlines(keepends=True),
        text2.splitlines(keepends=True),
        fromfile="Baseline Document",
        tofile="Draft Document",
        lineterm=""
    ))
    return ''.join(diff)

st.markdown("Upload a **baseline** and a **draft** PDF document to compare their contents.")

col1, col2 = st.columns(2)

with col1:
    pdf1 = st.file_uploader("Upload Baseline PDF", type="pdf", key="pdf1")

with col2:
    pdf2 = st.file_uploader("Upload Draft PDF", type="pdf", key="pdf2")

if pdf1 and pdf2:
    with st.spinner("Extracting and comparing text..."):
        text1 = extract_text_from_pdf(pdf1)
        text2 = extract_text_from_pdf(pdf2)
        diff = compare_texts(text1, text2)

    st.success("✅ Comparison Complete!")
    st.subheader("🔍 Differences")
    st.code(diff if diff else "No differences found!", language="diff")