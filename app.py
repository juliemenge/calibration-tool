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
/* ── Fonts & base ─────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
}

/* ── Hide Streamlit chrome ────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Tabs ─────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 2px solid #E5E0D8;
    padding-bottom: 0;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-weight: 600;
    font-size: 0.9rem;
    color: #7C7772;
    padding: 10px 18px;
    border-radius: 8px 8px 0 0;
    background: transparent;
    border: none;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #2D2B28 !important;
    border-bottom: 2px solid #C8602A !important;
}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    border-right: 1px solid #E5E0D8;
    background: #FAFAF8;
}
[data-testid="stSidebar"] .stMarkdown p {
    font-size: 13px;
    line-height: 1.85;
    color: #5C5752;
}
[data-testid="stSidebar"] h2 {
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #2D2B28 !important;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}

/* ── Metric cards ─────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E5E0D8;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: #7C7772 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    font-weight: 800 !important;
    font-size: 2rem !important;
    color: #2D2B28 !important;
}

/* ── Expanders (result cards) ─────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #E5E0D8 !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
    margin-bottom: 8px !important;
    background: #FFFFFF !important;
}
[data-testid="stExpander"] summary {
    padding: 14px 18px !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
}

/* ── File uploader ────────────────────────────────────── */
[data-testid="stFileUploader"] {
    border-radius: 10px;
    border: 1.5px dashed #D5CFC8 !important;
    background: #FAFAF8 !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #C8602A !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    font-size: 0.875rem !important;
    color: #7C7772 !important;
}

/* ── Buttons ──────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="primary"] {
    background: #C8602A !important;
    border: none !important;
    color: white !important;
    padding: 11px 28px !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 2px 6px rgba(200,96,42,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #B05525 !important;
    box-shadow: 0 3px 8px rgba(200,96,42,0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:disabled {
    background: #D5CFC8 !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ── Selectbox ────────────────────────────────────────── */
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    border-radius: 8px !important;
    border-color: #D5CFC8 !important;
}

/* ── Alerts / banners ─────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-width: 1px !important;
    font-size: 0.875rem !important;
}
.stSuccess { border-color: #A8D5A2 !important; }
.stInfo    { border-color: #B8D4E8 !important; }

/* ── Divider ──────────────────────────────────────────── */
hr { border-color: #E5E0D8 !important; margin: 1.5rem 0 !important; }

/* ── Dataframe ────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #E5E0D8;
}

/* ── Progress bar ─────────────────────────────────────── */
[data-testid="stProgress"] > div > div {
    background: #C8602A !important;
    border-radius: 4px !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# UI helpers: reusable styled components
# ─────────────────────────────────────────────
def step_header(num: int, title: str, desc: str):
    st.markdown(f"""
    <div style="display:flex;align-items:flex-start;gap:14px;
                padding:1.75rem 0 0.75rem;margin-top:0.25rem;">
        <div style="min-width:32px;height:32px;background:#C8602A;color:#fff;
                    border-radius:50%;display:flex;align-items:center;
                    justify-content:center;font-weight:700;font-size:0.875rem;
                    flex-shrink:0;box-shadow:0 2px 5px rgba(200,96,42,0.3);">{num}</div>
        <div>
            <div style="font-weight:700;font-size:1.1rem;color:#2D2B28;
                        line-height:1.3;">{title}</div>
            <div style="font-size:0.875rem;color:#7C7772;margin-top:3px;
                        line-height:1.5;">{desc}</div>
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
        f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
        f'<span style="color:#C8602A;font-size:0.9rem;">◦</span>'
        f'<span style="font-size:0.875rem;color:#5C5752;">{item}</span></div>'
        for item in items
    )
    st.markdown(f"""
    <div style="background:#FFF8F5;border:1px solid #E8C9BC;border-radius:10px;
                padding:14px 18px;margin:8px 0 16px;">
        <div style="font-weight:600;font-size:0.825rem;color:#7C3A1E;
                    text-transform:uppercase;letter-spacing:0.05em;
                    margin-bottom:8px;">Still needed to run</div>
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
    text_c, bg_c, border_c = colors_map.get(color, ("#2D2B28", "#F0EDE8", "#E5E0D8"))
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
        last  = tokens[-1] if len(tokens) > 1 else ""
    clean = lambda s: re.sub(r"[^a-z]", "", s.lower())
    return clean(first), clean(last)


def find_review_for_employee(name, pdf_dict):
    first, last = parse_name(name)
    if not first and not last:
        return None
    fn_lower = {fn: fn.lower() for fn in pdf_dict}
    candidates = []
    if first and last:
        candidates += [
            f"{first}-{last}", f"{last}-{first}",
            f"{first} {last}", f"{last} {first}",
            f"{last}_{first}", f"{first}_{last}",
        ]
    for fn, fln in fn_lower.items():
        for cand in candidates:
            if cand in fln:
                return pdf_dict[fn]
    if first and last:
        matches = [fn for fn, fln in fn_lower.items() if first in fln and last in fln]
        if matches:
            return pdf_dict[matches[0]]
    if last:
        matches = [fn for fn, fln in fn_lower.items() if last in fln]
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
        f'<div style="font-weight:600;font-size:0.875rem;color:#2D2B28;'
        f'margin-bottom:6px;">{emoji} {label}</div>',
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
        f'<div style="font-weight:700;font-size:0.95rem;color:#2D2B28;'
        f'margin-bottom:12px;">{label}</div>',
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
            '<p style="font-size:0.875rem;color:#A09A93;font-style:italic;'
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
    <div style="padding:2rem 0 1.25rem;">
        <h1 style="font-size:1.85rem;font-weight:800;color:#2D2B28;
                   letter-spacing:-0.5px;margin:0 0 6px;">
            Performance Review Calibration
        </h1>
        <p style="font-size:1rem;color:#7C7772;margin:0;line-height:1.5;">
            Upload your team's review materials to get a prioritised list
            of who needs discussion in your calibration session.
        </p>
    </div>
    <hr style="border-color:#E5E0D8;margin:0 0 0.5rem;">
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

    employee_data_file = st.file_uploader(
        "Employee data (CSV)", type=["csv"],
        label_visibility="collapsed",
        help="Required columns: Name, Level, Self Rating, Manager Rating",
    )
    st.markdown('<div style="margin-bottom:4px;font-size:0.875rem;color:#7C7772;">Upload a CSV with columns: <strong>Name</strong>, <strong>Level</strong>, <strong>Self Rating</strong>, <strong>Manager Rating</strong></div>', unsafe_allow_html=True)

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
    )
    st.markdown(
        '<div style="font-size:0.875rem;color:#7C7772;margin-top:4px;">'
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
        results = []
        progress_bar = st.progress(0.0)
        status_text  = st.empty()

        for i, row in employee_df.iterrows():
            name           = str(row["Name"]).strip()
            level          = str(row["Level"]).strip()
            self_rating    = row["Self Rating"]
            manager_rating = row["Manager Rating"]
            rating_gap     = abs(float(self_rating) - float(manager_rating))

            status_text.caption(f"Analysing {name}  ({i + 1} of {len(employee_df)})")

            self_review_text    = find_review_for_employee(name, self_reviews)    or "No self review provided."
            manager_review_text = find_review_for_employee(name, manager_reviews) or "No manager review provided."

            prompt = f"""You are an expert HR consultant helping a team prepare for a performance calibration session.
Your job is to analyze one employee's review data and determine how important they are to discuss,
and why. Be specific and grounded in the actual text provided.

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
Analyze this employee and return a JSON object with EXACTLY these fields:

{{
  "priority_score": <integer from 1 to 10, where 10 = most critical to discuss>,
  "primary_concern": "<one clear sentence summarizing the most important issue, or 'No significant flags' if clean>",
  "flags": [<list of specific flag strings — be concrete, e.g. "3-point rating gap", "manager narrative conflicts with strong self-rating">],
  "discussion_points": ["<specific point 1>", "<specific point 2>", "<specific point 3 if applicable>"],
  "rating_gap_concern": <true if the numeric gap is 1.5 or more points>,
  "narrative_rating_mismatch": <true if either written review doesn't match its corresponding numeric rating>,
  "self_manager_conflict": <true if the self and manager written narratives describe meaningfully different realities>
}}

Scoring guidance:
- 8–10: Multiple serious flags (large gap + narrative conflict, or evidence of bias/inconsistency)
- 5–7: One clear flag worth brief discussion (moderate gap, or one narrative mismatch)
- 2–4: Minor flags, likely fine to skip or spend < 2 minutes on
- 1: No concerns detected

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
            except Exception as e:
                analysis = {
                    "priority_score": min(10, max(1, int(rating_gap * 2.5))),
                    "primary_concern": f"AI analysis unavailable. Rating gap: {rating_gap:.1f} points.",
                    "flags": [f"{rating_gap:.1f}-point rating gap"] if rating_gap >= 1 else [],
                    "discussion_points": [],
                    "rating_gap_concern": rating_gap >= 1.5,
                    "narrative_rating_mismatch": False,
                    "self_manager_conflict": False,
                }

            results.append({
                "Name": name,
                "Level": level,
                "Self Rating": self_rating,
                "Manager Rating": manager_rating,
                "Gap": rating_gap,
                "Priority Score": analysis.get("priority_score", 1),
                "Primary Concern": analysis.get("primary_concern", ""),
                "Flags": analysis.get("flags", []),
                "Discussion Points": analysis.get("discussion_points", []),
                "rating_gap_concern": analysis.get("rating_gap_concern", False),
                "narrative_rating_mismatch": analysis.get("narrative_rating_mismatch", False),
                "self_manager_conflict": analysis.get("self_manager_conflict", False),
            })

            progress_bar.progress((i + 1) / len(employee_df))

        status_text.empty()
        progress_bar.empty()

        results_df = pd.DataFrame(results).sort_values("Priority Score", ascending=False).reset_index(drop=True)
        st.session_state["results"] = results_df

    # ── Results ────────────────────────────────────────────
    if "results" in st.session_state:
        results_df = st.session_state["results"]

        st.markdown('<hr style="border-color:#E5E0D8;margin:2rem 0 1.5rem;">', unsafe_allow_html=True)
        st.markdown(
            '<h2 style="font-size:1.4rem;font-weight:800;color:#2D2B28;'
            'margin:0 0 1.25rem;">Results</h2>',
            unsafe_allow_html=True,
        )

        total   = len(results_df)
        high_c  = len(results_df[results_df["Priority Score"] >= 7])
        mid_c   = len(results_df[(results_df["Priority Score"] >= 4) & (results_df["Priority Score"] < 7)])
        low_c   = len(results_df[results_df["Priority Score"] < 4])
        gap_c   = len(results_df[results_df["rating_gap_concern"] == True])
        narr_c  = len(results_df[results_df["narrative_rating_mismatch"] | results_df["self_manager_conflict"]])

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Employees", total)
        m2.metric("Need Discussion", high_c)
        m3.metric("Worth a Look", mid_c)
        m4.metric("Rating Gaps", gap_c)
        m5.metric("Narrative Flags", narr_c)

        # High priority
        section_pill("Discuss First", "red")
        high = results_df[results_df["Priority Score"] >= 7]
        if len(high) == 0:
            st.success("No employees flagged as high priority.")
        for _, row in high.iterrows():
            header = (
                f"**{row['Name']}** · {row['Level']} · "
                f"Score {row['Priority Score']}/10 · "
                f"Self {row['Self Rating']} → Manager {row['Manager Rating']}"
                f" (gap: {row['Gap']:.1f})"
            )
            with st.expander(header, expanded=True):
                st.markdown(f"**{row['Primary Concern']}**")
                flag_badges(row["rating_gap_concern"], row["narrative_rating_mismatch"], row["self_manager_conflict"])
                if row["Flags"]:
                    st.markdown("**Flags**")
                    for flag in row["Flags"]:
                        st.markdown(f"- {flag}")
                if row["Discussion Points"]:
                    st.markdown("**Suggested discussion points**")
                    for pt in row["Discussion Points"]:
                        st.markdown(f"- {pt}")

        # Medium priority
        section_pill("Worth a Look", "yellow")
        medium = results_df[(results_df["Priority Score"] >= 4) & (results_df["Priority Score"] < 7)]
        if len(medium) == 0:
            st.info("No medium-priority employees.")
        for _, row in medium.iterrows():
            header = (
                f"**{row['Name']}** · {row['Level']} · "
                f"Score {row['Priority Score']}/10 · "
                f"Self {row['Self Rating']} → Manager {row['Manager Rating']}"
                f" (gap: {row['Gap']:.1f})"
            )
            with st.expander(header):
                st.markdown(f"**{row['Primary Concern']}**")
                flag_badges(row["rating_gap_concern"], row["narrative_rating_mismatch"], row["self_manager_conflict"])
                if row["Flags"]:
                    for flag in row["Flags"]:
                        st.markdown(f"- {flag}")

        # Low priority
        section_pill("No Discussion Needed", "green")
        low = results_df[results_df["Priority Score"] < 4]
        if len(low) > 0:
            st.dataframe(
                low[["Name", "Level", "Self Rating", "Manager Rating", "Gap", "Primary Concern"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("All employees were flagged as medium or high priority.")

        # Export
        st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
        export_df = results_df[["Name","Level","Self Rating","Manager Rating","Gap","Priority Score","Primary Concern"]].copy()
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
    <div style="padding:2rem 0 1rem;">
        <h1 style="font-size:1.85rem;font-weight:800;color:#2D2B28;
                   letter-spacing:-0.5px;margin:0 0 6px;">
            File Library
        </h1>
        <p style="font-size:1rem;color:#7C7772;margin:0;line-height:1.5;">
            Save your career ladders and rating scales here once,
            and they'll be available to everyone using this tool — no re-uploading each time.
        </p>
    </div>
    <hr style="border-color:#E5E0D8;margin:0 0 1.5rem;">
    """, unsafe_allow_html=True)

    token, owner, repo = get_github_config()

    if not token:
        st.markdown("""
        <div style="background:#FFF8F5;border:1px solid #E8C9BC;border-radius:12px;
                    padding:20px 24px;max-width:560px;">
            <div style="font-weight:700;color:#2D2B28;margin-bottom:8px;">
                File Library isn't set up yet
            </div>
            <div style="font-size:0.875rem;color:#5C5752;line-height:1.65;">
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
            'background:#F0FAF0;border:1px solid #BBF7D0;border-radius:8px;'
            'padding:6px 14px;font-size:0.875rem;color:#166534;font-weight:600;'
            'margin-bottom:1.5rem;">✓ File Library connected</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p style="font-size:0.875rem;color:#5C5752;margin:0 0 1.5rem;">'
            'Upload a file and click <strong>Save to Library</strong>. '
            'It will appear in the dropdown on the Calibration tab within about a minute.</p>',
            unsafe_allow_html=True,
        )

        col_ladders, col_scales = st.columns(2)
        with col_ladders:
            file_library_section("Career Ladders", "career_ladders", token, owner, repo)
        with col_scales:
            file_library_section("Rating Scales", "rating_scales", token, owner, repo)

        st.markdown(
            '<p style="font-size:0.8rem;color:#A09A93;margin-top:2rem;">'
            'Files are stored in your connected repository and become available '
            'automatically after a short redeployment.</p>',
            unsafe_allow_html=True,
        )
