import streamlit as st
import pdfplumber
import difflib
import language_tool_python
import re
from collections import defaultdict
import pandas as pd
from io import BytesIO


def extract_text_from_pdf(uploaded_file):
    if uploaded_file is not None:
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        return text
    return ""


def split_by_chapter(text):
    chapters = defaultdict(str)
    current_chapter = "Preface or Unnumbered Section"
    for line in text.splitlines():
        chapter_match = re.match(r'^(\d+(?:\.\d+)*)(\s+.+)', line)
        if chapter_match:
            main_chapter = chapter_match.group(1)
            title = chapter_match.group(2).strip()
            current_chapter = f"{main_chapter} {title}"
            chapters[current_chapter] = ""
        chapters[current_chapter] += line + "\n"
    return chapters


def filter_content_only_diff(base_lines, draft_lines):
    diff = list(difflib.ndiff(base_lines, draft_lines))
    filtered_diff = [line for line in diff if line.startswith('+ ') or line.startswith('- ')]
    return filtered_diff


def calculate_similarity(base, draft):
    return difflib.SequenceMatcher(None, base, draft).ratio()


def find_renamed_chapters(baseline_chapters, draft_chapters):
    rename_map = {}
    base_keys = list(baseline_chapters.keys())
    draft_keys = list(draft_chapters.keys())

    for b_key in base_keys:
        base_content = baseline_chapters[b_key]
        best_match = None
        highest_score = 0.8  # Only consider matches above 80% similar
        for d_key in draft_keys:
            draft_content = draft_chapters[d_key]
            sim = calculate_similarity(base_content, draft_content)
            if sim > highest_score:
                best_match = d_key
                highest_score = sim
        if best_match:
            rename_map[b_key] = best_match
    return rename_map


def compare_chapters(baseline_text, draft_text):
    baseline_chapters = split_by_chapter(baseline_text)
    draft_chapters = split_by_chapter(draft_text)

    chapter_diffs = {}
    summary_rows = []

    rename_map = find_renamed_chapters(baseline_chapters, draft_chapters)
    matched_keys = set()

    for b_key, d_key in rename_map.items():
        matched_keys.add(d_key)
        base = baseline_chapters[b_key].splitlines()
        draft = draft_chapters[d_key].splitlines()
        filtered_diff = filter_content_only_diff(base, draft)
        chapter_diffs[d_key] = "\n".join(filtered_diff)
        similarity = calculate_similarity("\n".join(base), "\n".join(draft))

        for line in filtered_diff:
            if line.startswith('- '):
                summary_rows.append({"Chapter": d_key, "Type": "Removed from Baseline", "Content": line[2:], "Similarity": round(similarity, 2)})
            elif line.startswith('+ '):
                summary_rows.append({"Chapter": d_key, "Type": "Added in Draft", "Content": line[2:], "Similarity": round(similarity, 2)})

    # Handle unmatched chapters
    for chapter in draft_chapters:
        if chapter not in matched_keys:
            base = baseline_chapters.get(chapter, "").splitlines()
            draft = draft_chapters[chapter].splitlines()
            filtered_diff = filter_content_only_diff(base, draft)
            chapter_diffs[chapter] = "\n".join(filtered_diff)

            similarity = calculate_similarity("\n".join(base), "\n".join(draft))

            for line in filtered_diff:
                if line.startswith('- '):
                    summary_rows.append({"Chapter": chapter, "Type": "Removed from Baseline", "Content": line[2:], "Similarity": round(similarity, 2)})
                elif line.startswith('+ '):
                    summary_rows.append({"Chapter": chapter, "Type": "Added in Draft", "Content": line[2:], "Similarity": round(similarity, 2)})

    summary_df = pd.DataFrame(summary_rows)
    return chapter_diffs, summary_df


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
            if " by " in text.lower():  # simplistic passive voice detection
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


def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Summary')
    output.seek(0)
    return output


st.set_page_config(page_title="WindProof", layout="wide")
st.title("\U0001F32C️ WindProof - Full Proofreading Suite")

col1, col2 = st.columns(2)
with col1:
    baseline_file = st.file_uploader("\U0001F4C4 Upload Baseline Document (PDF)", type="pdf")
with col2:
    draft_file = st.file_uploader("\U0001F4DD Upload Draft Document (PDF)", type="pdf")

checklist_file = st.file_uploader("\U0001F4CB Upload Checklist File (TXT)", type="txt")
rules_file = st.file_uploader("\U0001F3F0 Upload Style Rules File (TXT)", type="txt")

if baseline_file and draft_file:
    baseline_text = extract_text_from_pdf(baseline_file)
    draft_text = extract_text_from_pdf(draft_file)

    st.subheader("\U0001F50D Chapterwise Content Differences")
    chapter_diffs, summary_df = compare_chapters(baseline_text, draft_text)

    for chapter, diff in chapter_diffs.items():
        if diff.strip():
            with st.expander(f"\U0001F4D8 {chapter}"):
                st.code(diff, language='diff')

    if not summary_df.empty:
        st.subheader("\U0001F4CA Summary of Changes with Similarity Score")
        st.dataframe(summary_df, use_container_width=True)

        excel_data = convert_df_to_excel(summary_df)
        st.download_button(
            label="\U0001F4BE Download Summary as Excel",
            data=excel_data,
            file_name="chapterwise_summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if checklist_file:
        checklist_items = checklist_file.read().decode("utf-8").splitlines()
        checklist_results = validate_checklist(draft_text, checklist_items)

        st.subheader("✅ Checklist Validation")
        for item, passed in checklist_results.items():
            st.write(f"{'✅' if passed else '❌'} {item}")

    if rules_file:
        rules = rules_file.read().decode("utf-8").splitlines()
        rule_findings = check_custom_rules(draft_text, rules)

        st.subheader("\U0001F3F0 Custom Style Rule Violations")
        if rule_findings:
            for finding in rule_findings:
                st.warning(finding)
        else:
            st.success("No violations found.")

    st.subheader("\U0001F4DA Grammar & Style Suggestions")
    grammar_matches = run_grammar_check(draft_text)
    if grammar_matches:
        for match in grammar_matches[:50]:  # limit output
            st.markdown(f"**Suggestion:** {match.message}<br>**At:** {match.context}", unsafe_allow_html=True)
    else:
        st.success("No grammar issues found.")
else:
    st.info("Please upload both baseline and draft PDF files to begin.")
