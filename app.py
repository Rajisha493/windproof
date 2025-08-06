import streamlit as st
import pdfplumber
import difflib
import language_tool_python

def extract_text_from_pdf(uploaded_file):
    if uploaded_file is not None:
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        return text
    return ""

def compare_texts(text1, text2):
    diff = difflib.unified_diff(
        text1.splitlines(),
        text2.splitlines(),
        fromfile='Baseline',
        tofile='Draft',
        lineterm=''
    )
    return '\n'.join(diff)

def validate_checklist(text, checklist_items):
    results = {}
    for item in checklist_items:
        results[item] = item.lower() in text.lower()
    return results

def check_custom_rules(text, rules):
    findings = []
    for rule in rules:
        rule_lower = rule.lower()
        if "passive voice" in rule_lower:
            if "by" in text.lower():  # simplistic passive voice detection
                findings.append("Potential passive voice detected (look for 'by').")
        elif "sentence length" in rule_lower:
            long_sentences = [s for s in text.split('.') if len(s.split()) > 25]
            if long_sentences:
                findings.append(f"{len(long_sentences)} long sentence(s) found (over 25 words).")
        elif "no use of the word" in rule_lower:
            keyword = rule_lower.replace("no use of the word", "").strip().strip('"')
            if keyword and keyword in text.lower():
                findings.append(f"Use of forbidden word: '{keyword}'")
        elif "no use of the phrase" in rule_lower:
            phrase = rule_lower.replace("no use of the phrase", "").strip().strip('"')
            if phrase and phrase in text.lower():
                findings.append(f"Use of forbidden phrase: '{phrase}'")
    return findings

def run_grammar_check(text):
    tool = language_tool_python.LanguageTool('en-US')
    matches = tool.check(text)
    return matches

st.set_page_config(page_title="WindProof", layout="wide")
st.title("🌬️ WindProof - Full Proofreading Suite")

col1, col2 = st.columns(2)
with col1:
    baseline_file = st.file_uploader("📄 Upload Baseline Document (PDF)", type="pdf")
with col2:
    draft_file = st.file_uploader("📝 Upload Draft Document (PDF)", type="pdf")

checklist_file = st.file_uploader("📋 Upload Checklist File (TXT)", type="txt")
rules_file = st.file_uploader("🛠️ Upload Style Rules File (TXT)", type="txt")

if baseline_file and draft_file:
    baseline_text = extract_text_from_pdf(baseline_file)
    draft_text = extract_text_from_pdf(draft_file)

    st.subheader("🔍 Text Differences")
    diff_result = compare_texts(baseline_text, draft_text)
    st.code(diff_result, language='diff')

    if checklist_file:
        checklist_items = checklist_file.read().decode("utf-8").splitlines()
        checklist_results = validate_checklist(draft_text, checklist_items)

        st.subheader("✅ Checklist Validation")
        for item, passed in checklist_results.items():
            st.write(f"{'✅' if passed else '❌'} {item}")

    if rules_file:
        rules = rules_file.read().decode("utf-8").splitlines()
        rule_findings = check_custom_rules(draft_text, rules)

        st.subheader("🛠️ Custom Style Rule Violations")
        if rule_findings:
            for finding in rule_findings:
                st.warning(finding)
        else:
            st.success("No violations found.")

    st.subheader("📚 Grammar & Style Suggestions")
    grammar_matches = run_grammar_check(draft_text)
    if grammar_matches:
        for match in grammar_matches[:50]:  # limit output
            st.markdown(f"**Suggestion:** {match.message}<br>**At:** {match.context}", unsafe_allow_html=True)
    else:
        st.success("No grammar issues found.")
else:
    st.info("Please upload both baseline and draft PDF files to begin.")
