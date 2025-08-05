import streamlit as st
import pdfplumber
from difflib import unified_diff

st.set_page_config(page_title="WindProof - PDF Comparator", layout="wide")
st.title("🌬️ WindProof - PDF Comparison + Checklist Validator")

# Extract text from PDF
def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# Compare two texts
def compare_texts(text1, text2):
    diff = list(unified_diff(
        text1.splitlines(keepends=True),
        text2.splitlines(keepends=True),
        fromfile="Baseline Document",
        tofile="Draft Document",
        lineterm=""
    ))
    return ''.join(diff)

# Validate draft against checklist items
def validate_checklist(draft_text, checklist_items):
    results = []
    for item in checklist_items:
        item_lower = item.lower()
        if '"' in item:
            quoted_phrase = item.split('"')[1]
            passed = quoted_phrase.lower() in draft_text.lower()
        elif "no use of the word" in item_lower:
            forbidden_word = item_lower.split("no use of the word")[1].strip().strip('"')
            passed = forbidden_word.lower() not in draft_text.lower()
        else:
            passed = item_lower in draft_text.lower()
        results.append((item, passed))
    return results

# File uploads
st.markdown("Upload a **baseline**, **draft**, and optional **checklist** file to run checks.")
col1, col2 = st.columns(2)

with col1:
    pdf1 = st.file_uploader("Upload Baseline PDF", type="pdf", key="pdf1")
with col2:
    pdf2 = st.file_uploader("Upload Draft PDF", type="pdf", key="pdf2")

checklist_file = st.file_uploader("📋 Upload Checklist File (TXT)", type="txt")

if pdf1 and pdf2:
    with st.spinner("Extracting and comparing text..."):
        text1 = extract_text_from_pdf(pdf1)
        text2 = extract_text_from_pdf(pdf2)
        diff = compare_texts(text1, text2)

    st.success("✅ Comparison Complete!")
    st.subheader("🔍 Differences")
    st.code(diff if diff else "No differences found!", language="diff")

    if checklist_file:
        checklist_text = checklist_file.read().decode("utf-8")
        checklist_items = [line.strip() for line in checklist_text.splitlines() if line.strip()]
        validation_results = validate_checklist(text2, checklist_items)

        st.subheader("📋 Checklist Validation Results")
        for item, passed in validation_results:
            st.write(f"{'✅' if passed else '❌'} {item}")
