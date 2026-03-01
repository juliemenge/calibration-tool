import streamlit as st
import anthropic
import pdfplumber
import pandas as pd
import json
import base64
import requests
from io import BytesIO
from pathlib import Path

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Calibration",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Fonts & base ─────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
}

/* ── Hide Streamlit chrome ────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Tabs ─────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #D8D4CC;
    padding-bottom: 0;
    background: transparent;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: "Inter", sans-serif;
    font-weight: 500;
    font-size: 0.875rem;
    color: #9C9690;
    padding: 12px 20px;
    background: transparent;
    border: none;
    letter-spacing: 0.01em;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #1A1918 !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #1A1918 !important;
}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    border-right: 1px solid #D8D4CC;
}
[data-testid="stSidebar"] .stMarkdown p {
    font-size: 13px;
    line-height: 1.85;
    color: #6C6762;
}
[data-testid="stSidebar"] h2 {
    font-family: "Inter", sans-serif !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    color: #9C9690 !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.75rem !important;
}

/* ── Metric cards ─────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #D8D4CC;
    border-radius: 12px;
    padding: 18px 22px;
}
[data-testid="stMetricLabel"] {
    font-family: "Inter", sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    color: #9C9690 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
[data-testid="stMetricValue"] {
    font-family: "DM Serif Display", serif !important;
    font-weight: 400 !important;
    font-size: 2.25rem !important;
    color: #1A1918 !important;
    letter-spacing: -0.5px;
}

/* ── Expanders (result cards) ─────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #D8D4CC !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    margin-bottom: 8px !important;
    background: #FFFFFF !important;
}
[data-testid="stExpander"] summary {
    padding: 16px 20px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: #1A1918 !important;
}

/* ── File uploader ────────────────────────────────────── */
[data-testid="stFileUploader"] {
    border-radius: 10px;
    border: 1.5px dashed #C8C3BB !important;
    background: #FFFFFF !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #1A1918 !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    font-size: 0.875rem !important;
    color: #9C9690 !important;
}

/* ── Buttons ──────────────────────────────────────────── */
.stButton > button {
    border-radius: 100px !important;
    font-family: "Inter", sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="primary"] {
    background: #1A1918 !important;
    border: none !important;
    color: #F5F4EF !important;
    padding: 12px 32px !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
}
.stButton > button[kind="primary"]:hover {
    background: #2D2B28 !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:disabled {
    background: #C8C3BB !important;
    color: #F5F4EF !important;
    transform: none !important;
}
.stButton > button[kind="secondary"] {
    border: 1px solid #C8C3BB !important;
    color: #1A1918 !important;
    background: transparent !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #1A1918 !important;
    background: transparent !important;
}

/* ── Selectbox ────────────────────────────────────────── */
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    border-radius: 10px !important;
    border-color: #C8C3BB !important;
    background: #FFFFFF !important;
}

/* ── Alerts / banners ─────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-width: 1px !important;
    font-size: 0.875rem !important;
}

/* ── Divider ──────────────────────────────────────────── */
hr { border-color: #D8D4CC !important; margin: 1.75rem 0 !important; }

/* ── Dataframe ────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #D8D4CC;
}

/* ── Progress bar ─────────────────────────────────────── */
[data-testid="stProgress"] > div > div {
    background: #1A1918 !important;
    border-radius: 4px !important;
}

/* ── Hide heading anchor links ────────────────────────── */
h1 a, h2 a, h3 a { display: none !important; }

/* ── Download button ──────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
    border-radius: 100px !important;
    border: 1px solid #C8C3BB !important;
    color: #1A1918 !important;
    background: transparent !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
}
[data-testid="stDownloadButton"] > button:hover {
    border-color: #1A1918 !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# UI helpers: reusable styled components
# ─────────────────────────────────────────────
def step_header(num: int, title: str, desc: str):
    st.markdown(f"""
    <div style="display:flex;align-items:flex-start;gap:16px;
                padding:2rem 0 0.75rem;margin-top:0.25rem;">
        <div style="min-width:28px;height:28px;background:#C8602A;color:#fff;
                    border-radius:50%;display:flex;align-items:center;
                    justify-content:center;font-family:'Inter',sans-serif;
                    font-weight:600;font-size:0.8rem;flex-shrink:0;
                    margin-top:3px;">{num}</div>
        <div>
            <div style="font-family:'DM Serif Display',serif;font-size:1.35rem;
                        color:#1A1918;line-height:1.25;letter-spacing:-0.2px;">{title}</div>
            <div style="font-family:'Inter',sans-serif;font-size:0.875rem;
                        color:#9C9690;margin-top:4px;line-height:1.5;">{desc}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def flag_badges(gap: bool, narrative: bool, conflict: bool):
    """Render pill-shaped flag badges inline."""
    badges = []
    if gap:
        badges.append('<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;font-size:11.5px;font-weight:600;background:#FEE2E2;color:#991B1B;border:1px solid #FECACA;">⚠ Rating gap</span>')
    if narrative:
        badges.append('<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;font-size:11.5px;font-weight:600;background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;">↕ Narrative mismatch</span>')
    if conflict:
        badges.append('<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;font-size:11.5px;font-weight:600;background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;">↔ Self vs. manager conflict</span>')
    if badges:
        st.markdown(
            '<div style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0;">' +
            "".join(badges) + "</div>",
            unsafe_allow_html=True
        )


def missing_checklist(items: list):
    """Render a soft checklist of items still needed before running."""
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:10px;padding:5px 0;">'
        f'<span style="color:#C8602A;font-size:1rem;line-height:1;">○</span>'
        f'<span style="font-family:Inter,sans-serif;font-size:0.875rem;color:#6C6762;">{item}</span></div>'
        for item in items
    )
    st.markdown(f"""
    <div style="background:#FFFFFF;border:1px solid #D8D4CC;border-radius:12px;
                padding:16px 20px;margin:8px 0 18px;">
        <div style="font-family:Inter,sans-serif;font-weight:600;font-size:0.72rem;
                    color:#9C9690;text-transform:uppercase;letter-spacing:0.08em;
                    margin-bottom:10px;">Still needed to run</div>
        {rows}
    </div>
    """, unsafe_allow_html=True)


def section_pill(label: str, color: str):
    """Render a coloured pill section label."""
    colors_map = {
        "red":    ("#991B1B", "#FEE2E2", "#FECACA"),
        "yellow": ("#92400E", "#FEF3C7", "#FDE68A"),
        "green":  ("#166534", "#DCFCE7", "#BBF7D0"),
    }
    text_c, bg_c, border_c = colors_map.get(color, ("#1A1918", "#ECEAE3", "#D8D4CC"))
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;padding:4px 14px;'
        f'border-radius:20px;background:{bg_c};border:1px solid {border_c};'
        f'color:{text_c};font-weight:700;font-size:0.8rem;letter-spacing:0.04em;'
        f'margin:1.5rem 0 0.75rem;">{label}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Settings")

    pre_configured_key = st.secrets.get("ANTHROPIC_API_KEY", "") if hasattr(st, "secrets") else ""

    if pre_configured_key:
        api_key = pre_configured_key
        st.success("AI analysis ready ✓")
    else:
        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder="sk-ant-…",
            help="Your Anthropic API key. Get one at console.anthropic.com.",
        )
        if api_key:
            st.success("API key saved ✓")

    st.divider()
    st.markdown("**How to use**")
    st.markdown(
        "1. Select or upload your career ladder and rating scale\n"
        "2. Upload your employee data spreadsheet\n"
        "3. Upload the review PDFs\n"
        "4. Click **Run Analysis**"
    )
    st.divider()
    st.markdown(
        "Save your career ladders and rating scales in the "
        "**File Library** tab so you don't have to re-upload them every time."
    )


# ─────────────────────────────────────────────
# Helpers: PDF / text extraction
# ─────────────────────────────────────────────
def extract_pdf_text(uploaded_file):
    text = ""
    try:
        uploaded_file.seek(0)
        with pdfplumber.open(BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        text = f"[Could not read file: {str(e)}]"
    return text.strip()


def read_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return ""
    if uploaded_file.type == "application/pdf":
        return extract_pdf_text(uploaded_file)
    uploaded_file.seek(0)
    return uploaded_file.read().decode("utf-8", errors="ignore")


def parse_name(name):
    import re
    name = name.strip()
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        last, first = parts[0], parts[1]
    else:
        tokens = name.split()
        first = tokens[0] if tokens else ""
        # Join remaining tokens so "Bille-Stauner" stays together
        last  = " ".join(tokens[1:]) if len(tokens) > 1 else ""
    # Preserve hyphens so "Bille-Stauner" → "bille-stauner" (not "billestauner")
    clean       = lambda s: re.sub(r"[^a-z\-]", "", s.lower())
    clean_plain = lambda s: re.sub(r"[^a-z]",    "", s.lower())
    return clean(first), clean(last), clean_plain(last)


def find_review_for_employee(name, pdf_dict):
    import re
    first, last, last_plain = parse_name(name)
    if not first and not last:
        return None

    fn_lower = {fn: fn.lower() for fn in pdf_dict}
    # Strip every non-alpha char for a last-resort fuzzy match
    fn_plain  = {fn: re.sub(r"[^a-z]", "", fn.lower()) for fn in pdf_dict}

    def make_candidates(f, l):
        return [
            f"{f}-{l}", f"{l}-{f}",
            f"{f} {l}", f"{l} {f}",
            f"{l}_{f}", f"{f}_{l}",
        ]

    candidates = []
    if first and last:
        candidates += make_candidates(first, last)
        # Also try with hyphens replaced by common separators in the filename
        last_dash  = last.replace("-", "_")
        last_space = last.replace("-", " ")
        candidates += make_candidates(first, last_dash)
        candidates += make_candidates(first, last_space)
    if first and last_plain and last_plain != last:
        # Hyphen-free version (e.g. filename has "BilleStauner" not "Bille-Stauner")
        candidates += make_candidates(first, last_plain)

    # Pass 1 — substring match on lowercased filename
    for fn, fln in fn_lower.items():
        for cand in candidates:
            if cand in fln:
                return pdf_dict[fn]

    # Pass 2 — both first and last appear anywhere in lowercased filename
    if first and last:
        matches = [fn for fn, fln in fn_lower.items()
                   if first in fln and (last in fln or last_plain in fln)]
        if matches:
            return pdf_dict[matches[0]]

    # Pass 3 — strip ALL separators from both sides and compare
    # e.g. "frankbillestauner" in "frankbillestauner_q1review"
    if first and last_plain:
        needle_fl = first + last_plain
        needle_lf = last_plain + first
        for fn, fpn in fn_plain.items():
            if needle_fl in fpn or needle_lf in fpn:
                return pdf_dict[fn]

    # Pass 4 — last name only (only if unique match)
    if last_plain:
        matches = [fn for fn, fpn in fn_plain.items() if last_plain in fpn]
        if len(matches) == 1:
            return pdf_dict[matches[0]]

    return None


def split_combined_review(uploaded_file):
    manager_pages, self_pages = [], []
    current_section = None
    try:
        uploaded_file.seek(0)
        with pdfplumber.open(BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                tl = text.lower()
                has_mgr  = "manager review" in tl
                has_self = "self review" in tl
                if has_mgr and has_self:
                    continue
                elif has_mgr:
                    current_section = "manager"
                    manager_pages.append(text)
                elif has_self:
                    current_section = "self"
                    self_pages.append(text)
                elif current_section == "manager":
                    manager_pages.append(text)
                elif current_section == "self":
                    self_pages.append(text)
    except Exception as e:
        return f"[Error reading file: {e}]", ""
    return "\n\n".join(manager_pages).strip(), "\n\n".join(self_pages).strip()


# ─────────────────────────────────────────────
# Pre-loaded library helpers (local disk)
# ─────────────────────────────────────────────
UPLOAD_OPTION = "⬆️  Upload a different file…"

def discover_preloaded(folder):
    p = Path(folder)
    if not p.exists():
        return []
    return sorted(
        f.name for f in p.iterdir()
        if f.suffix.lower() in (".pdf", ".txt")
        and not f.name.startswith(".")
        and f.stem.upper() not in ("README", "PLACEHOLDER")
    )


def read_source_file(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text.strip()
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def context_source_ui(label, emoji, folder, uploader_key, help_text):
    preloaded_names = discover_preloaded(folder)
    st.markdown(
        f'<div style="font-family:Inter,sans-serif;font-weight:600;font-size:0.825rem;'
        f'color:#1A1918;margin-bottom:6px;letter-spacing:0.01em;">{emoji} {label}</div>',
        unsafe_allow_html=True,
    )
    if preloaded_names:
        options = preloaded_names + [UPLOAD_OPTION]
        choice = st.selectbox(
            label, options,
            key=f"select_{uploader_key}",
            help=help_text,
            label_visibility="collapsed",
        )
        if choice == UPLOAD_OPTION:
            uploaded = st.file_uploader(
                "Upload file", type=["pdf", "txt"],
                key=f"upload_{uploader_key}",
                label_visibility="collapsed",
            )
            return None, uploaded
        else:
            st.caption(f"Using: {choice}")
            return Path(folder) / choice, None
    else:
        uploaded = st.file_uploader(
            "Upload PDF or text file", type=["pdf", "txt"],
            key=f"upload_{uploader_key}",
            help=help_text,
            label_visibility="collapsed",
        )
        return None, uploaded


# ─────────────────────────────────────────────
# GitHub API helpers (File Library)
# ─────────────────────────────────────────────
def get_github_config():
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo_full = st.secrets.get("GITHUB_REPO", "")
        if token and repo_full and "/" in repo_full:
            owner, repo_name = repo_full.split("/", 1)
            return token, owner, repo_name
    except Exception:
        pass
    return None, None, None


def github_list_files(token, owner, repo, folder):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return [
                {"name": f["name"], "sha": f["sha"], "size": f.get("size", 0)}
                for f in r.json()
                if f["type"] == "file"
                and f["name"].upper() not in ("README.TXT", "README.MD", "PLACEHOLDER.TXT")
                and not f["name"].startswith(".")
            ]
    except Exception:
        pass
    return []


def github_upload_file(token, owner, repo, folder, filename, content_bytes):
    path = f"{folder}/{filename}"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    encoded = base64.b64encode(content_bytes).decode("utf-8")
    body = {"message": f"Upload {filename} via Calibration Tool", "content": encoded}
    try:
        existing = requests.get(url, headers=headers, timeout=10)
        if existing.status_code == 200:
            body["sha"] = existing.json()["sha"]
            body["message"] = f"Update {filename} via Calibration Tool"
        r = requests.put(url, headers=headers, json=body, timeout=15)
        if r.status_code in (200, 201):
            return True, f"**{filename}** has been saved to the library."
        return False, r.json().get("message", r.text)
    except Exception as e:
        return False, str(e)


def github_delete_file(token, owner, repo, folder, filename, sha):
    path = f"{folder}/{filename}"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    body = {"message": f"Remove {filename} via Calibration Tool", "sha": sha}
    try:
        r = requests.delete(url, headers=headers, json=body, timeout=10)
        if r.status_code == 200:
            return True, f"**{filename}** has been removed."
        return False, r.json().get("message", r.text)
    except Exception as e:
        return False, str(e)


def file_library_section(label, folder, token, owner, repo):
    st.markdown(
        f'<div style="font-family:\'DM Serif Display\',serif;font-size:1.3rem;'
        f'color:#1A1918;margin-bottom:14px;">{label}</div>',
        unsafe_allow_html=True,
    )
    files = github_list_files(token, owner, repo, folder)
    if files:
        for f in files:
            col_name, col_size, col_btn = st.columns([5, 2, 1])
            size_kb = round(f["size"] / 1024, 1)
            col_name.markdown(f"📄 {f['name']}")
            col_size.caption(f"{size_kb} KB")
            if col_btn.button("✕", key=f"del_{folder}_{f['name']}", help=f"Remove {f['name']}"):
                ok, msg = github_delete_file(token, owner, repo, folder, f["name"], f["sha"])
                if ok:
                    st.success(msg + " The dropdown will update within about a minute.")
                else:
                    st.error(f"Something went wrong: {msg}")
                st.rerun()
    else:
        st.markdown(
            '<p style="font-family:Inter,sans-serif;font-size:0.875rem;color:#9C9690;'
            'margin:4px 0 16px;">No files saved yet.</p>',
            unsafe_allow_html=True,
        )

    new_file = st.file_uploader(
        f"Add a {label.rstrip('s').lower()} file",
        type=["pdf", "txt"],
        key=f"lib_upload_{folder}",
    )
    if new_file:
        if st.button("Save to Library", key=f"lib_save_{folder}", type="primary"):
            new_file.seek(0)
            ok, msg = github_upload_file(token, owner, repo, folder, new_file.name, new_file.read())
            if ok:
                st.success(f"✓ {msg} It will appear in the dropdown within about a minute.")
            else:
                st.error(f"Something went wrong — {msg}")


# ─────────────────────────────────────────────
# Tab layout
# ─────────────────────────────────────────────
tab_calibration, tab_library = st.tabs(["Calibration", "File Library"])


# ═════════════════════════════════════════════
# TAB 1 — CALIBRATION
# ═════════════════════════════════════════════
with tab_calibration:

    # Hero
    st.markdown("""
    <div style="padding:2.5rem 0 1.5rem;">
        <h1 style="font-family:'DM Serif Display',serif;font-size:2.75rem;
                   font-weight:400;color:#1A1918;letter-spacing:-0.5px;
                   line-height:1.15;margin:0 0 10px;">
            Performance Review<br>Calibration
        </h1>
        <p style="font-family:'Inter',sans-serif;font-size:1rem;color:#9C9690;
                  margin:0;line-height:1.6;max-width:520px;">
            Upload your team's review materials to get a prioritised list
            of who needs discussion in your calibration session.
        </p>
    </div>
    <hr style="border-color:#D8D4CC;margin:0 0 0.25rem;">
    """, unsafe_allow_html=True)

    # ── Step 1: Context documents ──────────────────────────
    step_header(1, "Context Documents",
                "These tell the tool what your career levels and rating definitions mean.")

    col1, col2 = st.columns(2)
    with col1:
        career_ladder_path, career_ladder_file = context_source_ui(
            label="Career Ladder", emoji="📋",
            folder="career_ladders", uploader_key="career_ladder",
            help_text="Your career ladder PDF. Save files in the File Library tab to keep them available permanently.",
        )
    with col2:
        rating_scale_path, rating_scale_file = context_source_ui(
            label="Rating Scale", emoji="⭐",
            folder="rating_scales", uploader_key="rating_scale",
            help_text="The rating definitions used in reviews. Save files in the File Library tab to keep them available permanently.",
        )

    # ── Step 2: Employee data ──────────────────────────────
    step_header(2, "Employee Data",
                "A spreadsheet with one row per employee and their self and manager ratings.")

    template_df = pd.DataFrame({
        "Name": ["Jane Smith", "John Doe", "Alex Johnson"],
        "Level": ["L4", "L5", "L4"],
        "Self Rating": [4, 3, 5],
        "Manager Rating": [2, 3, 4],
    })
    with st.expander("Download a template to get started"):
        st.dataframe(template_df, use_container_width=True)
        st.download_button(
            label="Download template",
            data=template_df.to_csv(index=False),
            file_name="calibration_template.csv",
            mime="text/csv",
        )

    _reset_n = st.session_state.get("upload_reset", 0)
    employee_data_file = st.file_uploader(
        "Employee data (CSV)", type=["csv"],
        label_visibility="collapsed",
        help="Required columns: Name, Level, Self Rating, Manager Rating",
        key=f"employee_csv_{_reset_n}",
    )
    st.markdown('<div style="font-family:Inter,sans-serif;margin-bottom:4px;font-size:0.82rem;color:#9C9690;">Required columns: <strong style="color:#1A1918;">Name</strong>, <strong style="color:#1A1918;">Level</strong>, <strong style="color:#1A1918;">Self Rating</strong>, <strong style="color:#1A1918;">Manager Rating</strong></div>', unsafe_allow_html=True)

    if employee_data_file:
        try:
            preview_df = pd.read_csv(employee_data_file)
            required_cols = {"Name", "Level", "Self Rating", "Manager Rating"}
            missing = required_cols - set(preview_df.columns)
            if missing:
                st.error(f"Missing columns: {', '.join(missing)}")
                employee_data_file = None
            else:
                st.success(f"{len(preview_df)} employees loaded ✓")
                employee_data_file.seek(0)
        except Exception as e:
            st.error(f"Couldn't read this file: {e}")
            employee_data_file = None

    # ── Step 3: Review packets ─────────────────────────────
    step_header(3, "Review Packets",
                "One PDF per employee. The tool will automatically find and separate "
                "the manager review and self review sections inside each file.")

    combined_review_files = st.file_uploader(
        "Review packets (PDFs)", type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Include the employee's name in each filename — e.g. Aaron-Brigham_Q1-2026.pdf",
        key=f"review_pdfs_{_reset_n}",
    )
    st.markdown(
        '<div style="font-family:Inter,sans-serif;font-size:0.82rem;color:#9C9690;margin-top:6px;">'
        'Include each employee\'s name in the filename so they can be matched to your spreadsheet.</div>',
        unsafe_allow_html=True,
    )

    if combined_review_files:
        st.caption(f"{len(combined_review_files)} file{'s' if len(combined_review_files) != 1 else ''} selected")

    # ── Run button ─────────────────────────────────────────
    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

    career_ladder_ready = bool(career_ladder_path or career_ladder_file)
    rating_scale_ready  = bool(rating_scale_path  or rating_scale_file)
    ready = bool(api_key and career_ladder_ready and rating_scale_ready and employee_data_file)

    if not ready:
        missing_items = []
        if not api_key:           missing_items.append("API key (in the sidebar)")
        if not career_ladder_ready: missing_items.append("Career ladder (Step 1)")
        if not rating_scale_ready:  missing_items.append("Rating scale (Step 1)")
        if not employee_data_file:  missing_items.append("Employee data (Step 2)")
        missing_checklist(missing_items)

    run_button = st.button("Run Analysis →", type="primary", disabled=not ready)

    # ── Helper: run analysis for a list of employee rows ──────────────
    def run_analysis_for_rows(employee_rows, self_reviews, manager_reviews,
                               career_ladder_text, rating_scale_text,
                               client, progress_offset=0, progress_total=None):
        """Analyse a list of employee dicts; return (results_list, unmatched_names)."""
        results = []
        unmatched = []
        n = len(employee_rows)
        if progress_total is None:
            progress_total = n
        progress_bar = st.progress(0.0)
        status_text  = st.empty()

        for idx, row in enumerate(employee_rows):
            name           = str(row["Name"]).strip()
            level          = str(row["Level"]).strip()
            self_rating    = row["Self Rating"]
            manager_rating = row["Manager Rating"]
            rating_gap     = abs(float(self_rating) - float(manager_rating))

            status_text.caption(f"Analysing {name}  ({progress_offset + idx + 1} of {progress_total})")

            mgr_text_raw  = find_review_for_employee(name, manager_reviews)
            self_text_raw = find_review_for_employee(name, self_reviews)

            if mgr_text_raw is None and self_text_raw is None:
                unmatched.append(name)

            manager_review_text = mgr_text_raw  or "No manager review provided."
            self_review_text    = self_text_raw or "No self review provided."

            prompt = f"""You are an expert HR consultant helping a team prepare for a performance calibration session.
Analyse one employee's review data and decide how much calibration discussion they warrant.
Be specific and grounded in the actual text provided.

━━━ CAREER LADDER ━━━
{career_ladder_text[:6000]}

━━━ RATING SCALE DEFINITIONS ━━━
{rating_scale_text[:3000]}

━━━ EMPLOYEE DETAILS ━━━
Name: {name}
Level: {level}
Self Rating: {self_rating}
Manager Rating: {manager_rating}
Rating Gap: {rating_gap:.1f} points

━━━ SELF REVIEW TEXT ━━━
{self_review_text[:10000]}

━━━ MANAGER REVIEW TEXT ━━━
{manager_review_text[:10000]}

━━━ YOUR TASK ━━━
Return a JSON object with EXACTLY these fields:

{{
  "tier": "<one of: discuss_first, worth_a_look, on_track>",
  "primary_concern": "<one clear sentence summarising the most important issue, or 'No significant concerns' if clean>",
  "flags": ["<specific flag — be concrete, e.g. '3-point self/manager gap', 'manager narrative conflicts with strong self-rating'>"],
  "discussion_points": ["<specific point 1>", "<specific point 2>", "<specific point 3 if applicable>"],
  "large_rating_gap": <true if the numeric gap between self and manager rating is 1.5 or more>,
  "narrative_contradicts_rating": <true if either written review does not match its corresponding numeric rating>,
  "self_manager_conflict": <true if the self and manager written narratives describe meaningfully different realities>
}}

Tier guidance:
- "discuss_first" — Large rating gap (1.5+ points), narrative that contradicts a rating, OR meaningful self/manager conflict. Needs calibration time.
- "worth_a_look" — Moderate gap (0.8–1.4 points) or a subtle mismatch worth brief attention. Low investment.
- "on_track" — Self and manager are well aligned and narratives support ratings. No meaningful concerns.

Respond ONLY with the JSON object. No preamble, no explanation outside the JSON."""

            try:
                response = client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}]
                )
                raw = response.content[0].text.strip()
                raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                analysis = json.loads(raw)
            except Exception:
                if rating_gap >= 1.5:
                    fallback_tier = "discuss_first"
                elif rating_gap >= 0.8:
                    fallback_tier = "worth_a_look"
                else:
                    fallback_tier = "on_track"
                analysis = {
                    "tier": fallback_tier,
                    "primary_concern": f"AI analysis unavailable. Rating gap: {rating_gap:.1f} points.",
                    "flags": [f"{rating_gap:.1f}-point rating gap"] if rating_gap >= 1 else [],
                    "discussion_points": [],
                    "large_rating_gap": rating_gap >= 1.5,
                    "narrative_contradicts_rating": False,
                    "self_manager_conflict": False,
                }

            results.append({
                "Name": name,
                "Level": level,
                "Self Rating": self_rating,
                "Manager Rating": manager_rating,
                "Gap": rating_gap,
                "Tier": analysis.get("tier", "on_track"),
                "Primary Concern": analysis.get("primary_concern", ""),
                "Flags": analysis.get("flags", []),
                "Discussion Points": analysis.get("discussion_points", []),
                "large_rating_gap": analysis.get("large_rating_gap", False),
                "narrative_contradicts_rating": analysis.get("narrative_contradicts_rating", False),
                "self_manager_conflict": analysis.get("self_manager_conflict", False),
            })

            progress_bar.progress((idx + 1) / n)

        status_text.empty()
        progress_bar.empty()
        return results, unmatched

    TIER_ORDER = {"discuss_first": 0, "worth_a_look": 1, "on_track": 2}

    def sort_by_tier(df):
        df = df.copy()
        df["_rank"] = df["Tier"].map(TIER_ORDER).fillna(3)
        return df.sort_values("_rank").drop(columns=["_rank"]).reset_index(drop=True)

    if run_button:
        with st.spinner("Reading documents…"):
            career_ladder_text = (
                read_source_file(career_ladder_path) if career_ladder_path
                else read_uploaded_file(career_ladder_file)
            )
            rating_scale_text = (
                read_source_file(rating_scale_path) if rating_scale_path
                else read_uploaded_file(rating_scale_file)
            )

        employee_df = pd.read_csv(employee_data_file)

        with st.spinner("Reading review packets…"):
            self_reviews, manager_reviews = {}, {}
            for f in (combined_review_files or []):
                mgr_text, self_text = split_combined_review(f)
                manager_reviews[f.name] = mgr_text
                self_reviews[f.name]    = self_text

        client = anthropic.Anthropic(api_key=api_key)

        employee_rows = employee_df.to_dict("records")
        results, unmatched = run_analysis_for_rows(
            employee_rows, self_reviews, manager_reviews,
            career_ladder_text, rating_scale_text, client,
            progress_total=len(employee_rows),
        )

        results_df = sort_by_tier(pd.DataFrame(results))
        st.session_state["results"]             = results_df
        st.session_state["unmatched"]           = unmatched
        st.session_state["career_ladder_text"]  = career_ladder_text
        st.session_state["rating_scale_text"]   = rating_scale_text
        st.session_state["employee_df_stored"]  = employee_df

    # ── Results ────────────────────────────────────────────
    if "results" in st.session_state:
        results_df = st.session_state["results"]

        st.markdown('<hr style="border-color:#D8D4CC;margin:2.5rem 0 1.75rem;">', unsafe_allow_html=True)

        # Results header + reset button side by side
        col_title, col_reset = st.columns([6, 1])
        with col_title:
            st.markdown(
                '<h2 style="font-family:\'DM Serif Display\',serif;font-size:2rem;'
                'font-weight:400;color:#1A1918;letter-spacing:-0.3px;'
                'margin:0 0 1.5rem;">Results</h2>',
                unsafe_allow_html=True,
            )
        with col_reset:
            st.markdown('<div style="margin-top:0.35rem;"></div>', unsafe_allow_html=True)
            if st.button("↩ Start over", type="secondary", key="reset_btn"):
                for key in ["results", "unmatched", "career_ladder_text",
                            "rating_scale_text", "employee_df_stored"]:
                    st.session_state.pop(key, None)
                st.session_state["upload_reset"] = st.session_state.get("upload_reset", 0) + 1
                st.rerun()

        # Metrics
        total     = len(results_df)
        discuss_c = len(results_df[results_df["Tier"] == "discuss_first"])
        look_c    = len(results_df[results_df["Tier"] == "worth_a_look"])
        track_c   = len(results_df[results_df["Tier"] == "on_track"])
        gap_c     = len(results_df[results_df["large_rating_gap"] == True])
        narr_c    = len(results_df[results_df["narrative_contradicts_rating"] | results_df["self_manager_conflict"]])

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Employees", total)
        m2.metric("Discuss First", discuss_c)
        m3.metric("Worth a Look", look_c)
        m4.metric("Rating Gaps", gap_c)
        m5.metric("Narrative Flags", narr_c)

        # ── Missing reviews warning + gap-fill ─────────────────────
        unmatched = st.session_state.get("unmatched", [])
        if unmatched:
            names_str = ", ".join(unmatched)
            st.markdown(f"""
            <div style="background:#FEF3C7;border:1px solid #FDE68A;border-radius:12px;
                        padding:16px 20px;margin:1.25rem 0;">
                <div style="font-family:Inter,sans-serif;font-weight:700;font-size:0.85rem;
                            color:#92400E;margin-bottom:6px;">
                    ⚠ No review PDF found for {len(unmatched)} employee{'s' if len(unmatched) != 1 else ''}
                </div>
                <div style="font-family:Inter,sans-serif;font-size:0.85rem;color:#92400E;
                            line-height:1.6;">
                    {names_str}<br>
                    <span style="color:#A85B10;">Upload their PDFs below and click <strong>Fill in gaps</strong> to re-run just these employees.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            gap_files = st.file_uploader(
                "Upload missing review PDFs",
                type=["pdf"],
                accept_multiple_files=True,
                key="gap_fill_files",
                label_visibility="collapsed",
            )
            if gap_files:
                st.caption(f"{len(gap_files)} file{'s' if len(gap_files) != 1 else ''} selected")
                if st.button("Fill in gaps →", type="primary", key="gap_fill_btn"):
                    # Split gap-fill PDFs
                    gap_self_reviews, gap_manager_reviews = {}, {}
                    for f in gap_files:
                        mgr_text, self_text = split_combined_review(f)
                        gap_manager_reviews[f.name] = mgr_text
                        gap_self_reviews[f.name]    = self_text

                    # Get stored context and find rows for unmatched employees
                    stored_df   = st.session_state.get("employee_df_stored", pd.DataFrame())
                    cl_text     = st.session_state.get("career_ladder_text", "")
                    rs_text     = st.session_state.get("rating_scale_text", "")
                    unmatched_rows = stored_df[stored_df["Name"].isin(unmatched)].to_dict("records")

                    gap_client = anthropic.Anthropic(api_key=api_key)
                    new_results, still_unmatched = run_analysis_for_rows(
                        unmatched_rows, gap_self_reviews, gap_manager_reviews,
                        cl_text, rs_text, gap_client,
                        progress_total=len(unmatched_rows),
                    )

                    # Replace old rows, re-sort
                    new_names = [r["Name"] for r in new_results]
                    existing  = results_df[~results_df["Name"].isin(new_names)]
                    merged    = sort_by_tier(
                        pd.concat([existing, pd.DataFrame(new_results)], ignore_index=True)
                    )
                    st.session_state["results"]   = merged
                    st.session_state["unmatched"] = still_unmatched
                    st.rerun()

        # ── Discuss First ───────────────────────────────────────────
        section_pill("🔴  Discuss First", "red")
        discuss = results_df[results_df["Tier"] == "discuss_first"]
        if len(discuss) == 0:
            st.success("No employees flagged for immediate discussion.")
        for _, row in discuss.iterrows():
            gap_label = f"gap: {row['Gap']:.1f}" if row['Gap'] > 0 else "no gap"
            header = (
                f"**{row['Name']}** · {row['Level']} · "
                f"Self {row['Self Rating']} → Manager {row['Manager Rating']}"
                f"  ({gap_label})"
            )
            with st.expander(header, expanded=True):
                st.markdown(f"**{row['Primary Concern']}**")
                flag_badges(row["large_rating_gap"], row["narrative_contradicts_rating"], row["self_manager_conflict"])
                if row["Flags"]:
                    st.markdown("**Flags**")
                    for flag in row["Flags"]:
                        st.markdown(f"- {flag}")
                if row["Discussion Points"]:
                    st.markdown("**Suggested discussion points**")
                    for pt in row["Discussion Points"]:
                        st.markdown(f"- {pt}")

        # ── Worth a Look ────────────────────────────────────────────
        section_pill("🟡  Worth a Look", "yellow")
        look = results_df[results_df["Tier"] == "worth_a_look"]
        if len(look) == 0:
            st.info("No employees in this tier.")
        for _, row in look.iterrows():
            gap_label = f"gap: {row['Gap']:.1f}" if row['Gap'] > 0 else "no gap"
            header = (
                f"**{row['Name']}** · {row['Level']} · "
                f"Self {row['Self Rating']} → Manager {row['Manager Rating']}"
                f"  ({gap_label})"
            )
            with st.expander(header):
                st.markdown(f"**{row['Primary Concern']}**")
                flag_badges(row["large_rating_gap"], row["narrative_contradicts_rating"], row["self_manager_conflict"])
                if row["Flags"]:
                    for flag in row["Flags"]:
                        st.markdown(f"- {flag}")
                if row["Discussion Points"]:
                    for pt in row["Discussion Points"]:
                        st.markdown(f"- {pt}")

        # ── On Track ────────────────────────────────────────────────
        section_pill("🟢  On Track", "green")
        on_track = results_df[results_df["Tier"] == "on_track"]
        if len(on_track) > 0:
            st.dataframe(
                on_track[["Name", "Level", "Self Rating", "Manager Rating", "Gap", "Primary Concern"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("All employees have at least minor flags — none landed in On Track.")

        # Export
        st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
        export_df = results_df[["Name", "Level", "Self Rating", "Manager Rating",
                                 "Gap", "Tier", "Primary Concern"]].copy()
        st.download_button(
            label="Download results as CSV",
            data=export_df.to_csv(index=False),
            file_name="calibration_results.csv",
            mime="text/csv",
        )


# ═════════════════════════════════════════════
# TAB 2 — FILE LIBRARY
# ═════════════════════════════════════════════
with tab_library:

    st.markdown("""
    <div style="padding:2.5rem 0 1.5rem;">
        <h1 style="font-family:'DM Serif Display',serif;font-size:2.75rem;
                   font-weight:400;color:#1A1918;letter-spacing:-0.5px;
                   line-height:1.15;margin:0 0 10px;">
            File Library
        </h1>
        <p style="font-family:'Inter',sans-serif;font-size:1rem;color:#9C9690;
                  margin:0;line-height:1.6;max-width:520px;">
            Save your career ladders and rating scales here once,
            and they'll be available to everyone using this tool — no re-uploading each time.
        </p>
    </div>
    <hr style="border-color:#D8D4CC;margin:0 0 1.5rem;">
    """, unsafe_allow_html=True)

    token, owner, repo = get_github_config()

    if not token:
        st.markdown("""
        <div style="background:#FFFFFF;border:1px solid #D8D4CC;border-radius:14px;
                    padding:22px 26px;max-width:540px;">
            <div style="font-family:'DM Serif Display',serif;font-size:1.2rem;
                        color:#1A1918;margin-bottom:8px;">
                File Library isn't set up yet
            </div>
            <div style="font-family:Inter,sans-serif;font-size:0.875rem;
                        color:#6C6762;line-height:1.7;">
                To enable it, add <code>GITHUB_TOKEN</code> and <code>GITHUB_REPO</code>
                to your app's Secrets in Streamlit. See <strong>HOW_TO_DEPLOY.md</strong>
                for step-by-step instructions.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
        st.info(
            "In the meantime, you can still upload career ladders and rating scales "
            "directly in Step 1 of the Calibration tab for each session."
        )
    else:
        st.markdown(
            '<div style="display:inline-flex;align-items:center;gap:8px;'
            'background:#FFFFFF;border:1px solid #D8D4CC;border-radius:100px;'
            'padding:5px 14px;font-family:Inter,sans-serif;font-size:0.8rem;'
            'color:#1A1918;font-weight:500;margin-bottom:1.5rem;">'
            '<span style="color:#C8602A;">●</span> Library connected</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p style="font-family:Inter,sans-serif;font-size:0.9rem;color:#6C6762;margin:0 0 1.5rem;">'
            'Upload a file and click <strong style="color:#1A1918;">Save to Library</strong>. '
            'It will appear in the dropdown on the Calibration tab within about a minute.</p>',
            unsafe_allow_html=True,
        )

        col_ladders, col_scales = st.columns(2)
        with col_ladders:
            file_library_section("Career Ladders", "career_ladders", token, owner, repo)
        with col_scales:
            file_library_section("Rating Scales", "rating_scales", token, owner, repo)

        st.markdown(
            '<p style="font-family:Inter,sans-serif;font-size:0.8rem;color:#9C9690;margin-top:2rem;">'
            'Files are stored in your connected repository and become available '
            'automatically after a short redeployment.</p>',
            unsafe_allow_html=True,
        )
