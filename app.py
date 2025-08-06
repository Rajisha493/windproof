import streamlit as st
import pdfplumber
from difflib import unified_diff
import re
import language_tool_python

st.set_page_config(page_title="WindProof", layout="wide")
st.title("🌬️ WindProof - Full Proofreading Suite")

# Extract text from PDF
def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# Compare baseline and draft
def compare_texts(text1, text2):
    diff = list(unified_diff(
        text1.splitlines(keepends=True),
        text2.splitlines(keepends=True),
        fromfile="Baseline Document",
        tofile="Draft Document",
        lineterm=""
    ))
    return ''.join(diff)

# Checklist validation
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

# Custom rule checks
def check_style_issues(text, rules):
    results = []
    sentences = re.split(r'(?<=[.!?]) +', text)
    for i, sentence in enumerate(sentences):
        if len(sentence.split()) > 25:
            results.append((f"Sentence {i+1} exceeds 25 words", False))
        if re.search(r'\b(is|was|were|be|been|being|are|am)\b.*\b(by)\b', sentence):
            results.append((f"Sentence {i+1} may use passive voice", False))

    for rule in rules:
        if '"' in rule:
            phrase = rule.split('"')[1].lower()
            if phrase in text.lower():
                results.append((f'Use of forbidden phrase: "{phrase}"', False))
        elif "passive voice" in rule.lower() or "sentence length" in rule.lower():
            continue  # already checked
        else:
            results.append((f"Unrecognized rule: {rule}", False))
    return results

# Grammar check using LanguageTool
def run_grammar_check(text):
    tool = language_tool_python.LanguageTool('en-US')
    return tool.check(text)

# Upload documents
col1, col2 = st.columns(2)
with col1:
    pdf1 = st.file_uploader("Upload Baseline PDF", type="pdf", key="pdf1")
with col2:
    pdf2 = st.file_uploader("Upload Draft PDF", type="pdf", key="pdf2")

checklist_file = st.file_uploader("\ud83d\udccb Upload Checklist File (TXT)", type="txt")
rules_file = st.file_uploader("\ud83d\udee0\ufe0f Upload Custom Rules File (TXT)", type="txt")

if pdf1 and pdf2:
    with st.spinner("Processing documents..."):
        text1 = extract_text_from_pdf(pdf1)
        text2 = extract_text_from_pdf(pdf2)
        diff = compare_texts(text1, text2)

    st.success("\u2705 Comparison Complete!")
    st.subheader("\ud83d\udd0d Differences")
    st.code(diff if diff else "No differences found!", language="diff")

    if checklist_file:
        checklist_text = checklist_file.read().decode("utf-8")
        checklist_items = [line.strip() for line in checklist_text.splitlines() if line.strip()]
        checklist_results = validate_checklist(text2, checklist_items)

        st.subheader("\ud83d\udccb Checklist Validation")
        for item, passed in checklist_results:
            st.write(f"{'\u2705' if passed else '\u274c'} {item}")

    if rules_file:
        rules_text = rules_file.read().decode("utf-8")
        rule_items = [line.strip() for line in rules_text.splitlines() if line.strip()]
        style_issues = check_style_issues(text2, rule_items)

        st.subheader("\ud83d\udee0\ufe0f Style Rule Checks")
        if not style_issues:
            st.success("No major style issues found \u2705")
        else:
            for issue, _ in style_issues:
                st.write(f"\u274c {issue}")

    with st.spinner("Running grammar checks..."):
        matches = run_grammar_check(text2)

    st.subheader("\ud83d\udcda Grammar Suggestions (LanguageTool)")
    if not matches:
        st.success("No grammar or spelling issues found \u2705")
    else:
        for match in matches:
            st.markdown(f"- \u274c **{match.message}**")
            if match.replacements:
                st.markdown(f"  \u21aa Suggested: `{', '.join(match.replacements)}`")

