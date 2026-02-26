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
    page_title="Calibration Tool",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
/* ── Global type & spacing ─────────────────────────── */
html, body, [class*="css"] {
    font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
}
h1 { font-weight: 800; letter-spacing: -0.5px; }
h2 { font-weight: 700; letter-spacing: -0.3px; }
h3 { font-weight: 700; }

/* ── Sidebar refinements ───────────────────────────── */
[data-testid="stSidebar"] {
    border-right: 1px solid #E5E0D8;
}
[data-testid="stSidebar"] .stMarkdown p {
    font-size: 13px;
    line-height: 1.9;
    color: #5C5752;
}

/* ── Metric cards ──────────────────────────────────── */
[data-testid="stMetric"] {
    background: #FAFAF8;
    border: 1px solid #E5E0D8;
    border-radius: 10px;
    padding: 14px 18px;
}
[data-testid="stMetricValue"] { font-weight: 800; }

/* ── File uploader ─────────────────────────────────── */
[data-testid="stFileUploader"] {
    border-radius: 8px;
}

/* ── Expander ──────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #E5E0D8 !important;
    border-radius: 8px !important;
}

/* ── Primary button ────────────────────────────────── */
.stButton > button[kind="primary"] {
    font-weight: 700;
    letter-spacing: 0.2px;
    border-radius: 8px;
    padding: 10px 28px;
}

/* ── Divider ───────────────────────────────────────── */
hr { border-color: #E5E0D8 !important; }

/* ── Info / success banners ────────────────────────── */
[data-testid="stAlert"] { border-radius: 8px; }

/* ── Library file row ──────────────────────────────── */
.library-file-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    border: 1px solid #E5E0D8;
    border-radius: 8px;
    margin-bottom: 8px;
    background: #FAFAF8;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar: API key
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    pre_configured_key = st.secrets.get("ANTHROPIC_API_KEY", "") if hasattr(st, "secrets") else ""

    if pre_configured_key:
        api_key = pre_configured_key
        st.success("API key configured ✓")
    else:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            help="Get one at console.anthropic.com — you'll need to create an account and add a payment method."
        )
        if api_key:
            st.success("API key entered ✓")

    st.divider()
    st.markdown("**How to use:**")
    st.markdown("1. Enter your API key")
    st.markdown("2. Upload context docs (career ladder + rating scale)")
    st.markdown("3. Upload your employee data CSV")
    st.markdown("4. Upload combined review packets (one PDF per employee)")
    st.markdown("5. Click **Run Analysis**")
    st.divider()
    st.markdown("Use the **File Library** tab to save career ladders and rating scales so they're always available — no re-uploading needed.")


# ─────────────────────────────────────────────
# Helper: PDF / text extraction
# ─────────────────────────────────────────────
def extract_pdf_text(uploaded_file):
    """Extract all text from an uploaded PDF file."""
    text = ""
    try:
        uploaded_file.seek(0)
        with pdfplumber.open(BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        text = f"[Could not extract text from {uploaded_file.name}: {str(e)}]"
    return text.strip()


def read_uploaded_file(uploaded_file):
    """Read either a PDF or a plain text file and return its text content."""
    if uploaded_file is None:
        return ""
    if uploaded_file.type == "application/pdf":
        return extract_pdf_text(uploaded_file)
    else:
        uploaded_file.seek(0)
        return uploaded_file.read().decode("utf-8", errors="ignore")


def parse_name(name):
    """
    Parse a name string into (first, last) regardless of format.
    Handles:
      - "Justin Wolfe"   → ("justin", "wolfe")
      - "Wolfe, Justin"  → ("justin", "wolfe")   ← Lattice CSV export format
      - "Justin M Wolfe" → ("justin", "wolfe")
    Returns lowercase strings with punctuation stripped.
    """
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
    """
    Match an employee name to the right file in pdf_dict {filename: text}.
    Handles Lattice-style filenames with email prefixes and hyphenated names.
    """
    first, last = parse_name(name)
    if not first and not last:
        return None

    fn_lower = {fn: fn.lower() for fn in pdf_dict}
    candidates = []
    if first and last:
        candidates += [
            f"{first}-{last}",
            f"{last}-{first}",
            f"{first} {last}",
            f"{last} {first}",
            f"{last}_{first}",
            f"{first}_{last}",
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
    """
    Split a combined review packet PDF into manager review text and self review text.
    Scans page by page; pages containing BOTH markers are treated as TOC/cover pages.
    Returns (manager_text, self_text).
    """
    manager_pages = []
    self_pages = []
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
                    continue  # TOC page
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
# Pre-loaded file library helpers (local disk)
# ─────────────────────────────────────────────
UPLOAD_OPTION = "⬆️  Upload a different file…"

def discover_preloaded(folder):
    """Return sorted list of PDF/TXT filenames in `folder`, ignoring README/placeholder files."""
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
    """Read text from a pre-loaded file on disk (PDF or plain text)."""
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
    """
    Render a context-document selector: dropdown of pre-loaded files when available,
    with an upload fallback. Returns (preloaded_path_or_None, uploaded_file_or_None).
    """
    preloaded_names = discover_preloaded(folder)
    st.markdown(f"**{emoji} {label}**")

    if preloaded_names:
        options = preloaded_names + [UPLOAD_OPTION]
        choice = st.selectbox(
            f"Select {label.lower()}",
            options,
            key=f"select_{uploader_key}",
            help=help_text,
            label_visibility="collapsed",
        )
        if choice == UPLOAD_OPTION:
            uploaded = st.file_uploader(
                f"Upload {label.lower()}",
                type=["pdf", "txt"],
                key=f"upload_{uploader_key}",
                label_visibility="collapsed",
            )
            return None, uploaded
        else:
            st.caption(f"Using saved file: {choice}")
            return Path(folder) / choice, None
    else:
        uploaded = st.file_uploader(
            f"Upload {label.lower()} (PDF or TXT)",
            type=["pdf", "txt"],
            key=f"upload_{uploader_key}",
            help=help_text,
            label_visibility="collapsed",
        )
        return None, uploaded


# ─────────────────────────────────────────────
# GitHub API helpers (for File Library tab)
# ─────────────────────────────────────────────
def get_github_config():
    """
    Read GitHub credentials from Streamlit secrets.
    Returns (token, owner, repo_name) or (None, None, None) if not configured.
    GITHUB_REPO should be in "owner/repo" format, e.g. "juliemenge/calibration-tool".
    """
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
    """
    List non-README files in a GitHub repo folder.
    Returns list of dicts: [{name, sha, size}] or [] on error.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
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
    """
    Upload (create or replace) a file in a GitHub repo folder.
    Returns (True, message) or (False, error_message).
    """
    path = f"{folder}/{filename}"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    encoded = base64.b64encode(content_bytes).decode("utf-8")
    body = {
        "message": f"Upload {filename} via Calibration Tool",
        "content": encoded,
    }
    try:
        # Check if file already exists — need its SHA to overwrite
        existing = requests.get(url, headers=headers, timeout=10)
        if existing.status_code == 200:
            body["sha"] = existing.json()["sha"]
            body["message"] = f"Update {filename} via Calibration Tool"

        r = requests.put(url, headers=headers, json=body, timeout=15)
        if r.status_code in (200, 201):
            return True, f"✅ **{filename}** saved to the library."
        else:
            detail = r.json().get("message", r.text)
            return False, f"GitHub error ({r.status_code}): {detail}"
    except Exception as e:
        return False, f"Request failed: {str(e)}"


def github_delete_file(token, owner, repo, folder, filename, sha):
    """
    Delete a file from a GitHub repo folder.
    Returns (True, message) or (False, error_message).
    """
    path = f"{folder}/{filename}"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    body = {
        "message": f"Remove {filename} via Calibration Tool",
        "sha": sha,
    }
    try:
        r = requests.delete(url, headers=headers, json=body, timeout=10)
        if r.status_code == 200:
            return True, f"🗑️ **{filename}** removed from the library."
        else:
            detail = r.json().get("message", r.text)
            return False, f"GitHub error ({r.status_code}): {detail}"
    except Exception as e:
        return False, f"Request failed: {str(e)}"


def file_library_section(label, folder, token, owner, repo):
    """
    Render a single file library section (career ladders OR rating scales).
    Shows current files with delete buttons, and an uploader to add new files.
    """
    st.markdown(f"#### {label}")

    # ── Existing files ──
    files = github_list_files(token, owner, repo, folder)
    if files:
        for f in files:
            col_name, col_size, col_btn = st.columns([5, 2, 1])
            size_kb = round(f["size"] / 1024, 1)
            col_name.markdown(f"📄 **{f['name']}**")
            col_size.caption(f"{size_kb} KB")
            if col_btn.button("🗑️", key=f"del_{folder}_{f['name']}", help=f"Delete {f['name']}"):
                ok, msg = github_delete_file(token, owner, repo, folder, f["name"], f["sha"])
                if ok:
                    st.success(msg + " Refresh in ~60 seconds for it to disappear from the dropdown.")
                else:
                    st.error(msg)
                st.rerun()
    else:
        st.caption("No files saved yet.")

    # ── Upload new file ──
    new_file = st.file_uploader(
        f"Add a new {label.lower()} file",
        type=["pdf", "txt"],
        key=f"lib_upload_{folder}",
        label_visibility="visible",
    )
    if new_file:
        if st.button(f"Save to Library", key=f"lib_save_{folder}", type="primary"):
            new_file.seek(0)
            ok, msg = github_upload_file(
                token, owner, repo, folder, new_file.name, new_file.read()
            )
            if ok:
                st.success(msg + "\n\nStreamlit will redeploy automatically — your file will appear in the Step 1 dropdown within about 60 seconds.")
            else:
                st.error(msg)


# ─────────────────────────────────────────────
# Tab layout
# ─────────────────────────────────────────────
tab_calibration, tab_library = st.tabs(["🎯 Calibration", "📁 File Library"])


# ═════════════════════════════════════════════
# TAB 1 — CALIBRATION
# ═════════════════════════════════════════════
with tab_calibration:

    st.title("🎯 Performance Review Calibration Tool")
    st.markdown(
        "Upload your materials below and the tool will identify who most needs discussion in your calibration session."
    )

    # ── Step 1: Context documents ──────────────────────
    st.divider()
    st.header("Step 1 — Context Documents")
    st.markdown(
        "These teach the tool what your company's career ladder and rating definitions actually mean."
    )

    col1, col2 = st.columns(2)
    with col1:
        career_ladder_path, career_ladder_file = context_source_ui(
            label="Career Ladder",
            emoji="📋",
            folder="career_ladders",
            uploader_key="career_ladder",
            help_text="Your career ladder with level definitions. Save files via the File Library tab to make them permanently available here.",
        )
    with col2:
        rating_scale_path, rating_scale_file = context_source_ui(
            label="Rating Scale & Definitions",
            emoji="⭐",
            folder="rating_scales",
            uploader_key="rating_scale",
            help_text="The rating scale used in reviews. Save files via the File Library tab to make them permanently available here.",
        )

    # ── Step 2: Employee data CSV ──────────────────────
    st.divider()
    st.header("Step 2 — Employee Data")
    st.markdown(
        "Upload a CSV with one row per employee. Required columns: **Name**, **Level**, "
        "**Self Rating**, **Manager Rating**."
    )

    template_df = pd.DataFrame({
        "Name": ["Jane Smith", "John Doe", "Alex Johnson"],
        "Level": ["L4", "L5", "L4"],
        "Self Rating": [4, 3, 5],
        "Manager Rating": [2, 3, 4],
    })
    with st.expander("📥 Download a CSV template to get started"):
        st.dataframe(template_df, use_container_width=True)
        st.download_button(
            label="Download template CSV",
            data=template_df.to_csv(index=False),
            file_name="calibration_template.csv",
            mime="text/csv",
        )

    employee_data_file = st.file_uploader("📊 Employee Data (CSV)", type=["csv"])

    if employee_data_file:
        try:
            preview_df = pd.read_csv(employee_data_file)
            required_cols = {"Name", "Level", "Self Rating", "Manager Rating"}
            missing = required_cols - set(preview_df.columns)
            if missing:
                st.error(f"Missing required columns: {', '.join(missing)}")
                employee_data_file = None
            else:
                st.success(f"{len(preview_df)} employees loaded ✓")
                employee_data_file.seek(0)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            employee_data_file = None

    # ── Step 3: Review packets ─────────────────────────
    st.divider()
    st.header("Step 3 — Review Packets")
    st.markdown(
        "Upload one combined review packet PDF per employee — the tool will automatically detect "
        "and split the manager review and self review sections. "
        "**Include the employee's name in each filename** so they can be matched to your CSV "
        "— e.g. `Aaron-Brigham_2026-Q1-Performance-Assessment.pdf`."
    )

    combined_review_files = st.file_uploader(
        "📝 Combined Review Packets (PDFs)",
        type=["pdf"],
        accept_multiple_files=True,
        help="One packet per employee. The tool expects a 'Manager review' section and a 'Self review' section inside each PDF."
    )

    if combined_review_files:
        st.caption(f"{len(combined_review_files)} packet(s) uploaded: {', '.join([f.name for f in combined_review_files])}")

    # ── Run button ─────────────────────────────────────
    st.divider()

    career_ladder_ready = bool(career_ladder_path or career_ladder_file)
    rating_scale_ready  = bool(rating_scale_path  or rating_scale_file)
    ready = bool(api_key and career_ladder_ready and rating_scale_ready and employee_data_file)

    if not ready:
        missing_items = []
        if not api_key:
            missing_items.append("Anthropic API key")
        if not career_ladder_ready:
            missing_items.append("Career Ladder")
        if not rating_scale_ready:
            missing_items.append("Rating Scale")
        if not employee_data_file:
            missing_items.append("Employee Data CSV")
        st.info(f"Still needed to run: {', '.join(missing_items)}")

    run_button = st.button("🚀 Run Calibration Analysis", type="primary", disabled=not ready)

    if run_button:
        with st.spinner("Reading context documents..."):
            career_ladder_text = (
                read_source_file(career_ladder_path)
                if career_ladder_path
                else read_uploaded_file(career_ladder_file)
            )
            rating_scale_text = (
                read_source_file(rating_scale_path)
                if rating_scale_path
                else read_uploaded_file(rating_scale_file)
            )

        employee_df = pd.read_csv(employee_data_file)

        with st.spinner("Extracting and splitting review packets..."):
            self_reviews = {}
            manager_reviews = {}
            split_preview = []
            for f in (combined_review_files or []):
                mgr_text, self_text = split_combined_review(f)
                manager_reviews[f.name] = mgr_text
                self_reviews[f.name]    = self_text
                split_preview.append(
                    f"**{f.name}** — manager: {len(mgr_text)} chars, self: {len(self_text)} chars"
                )
            if split_preview:
                with st.expander("📋 Packet split preview", expanded=False):
                    for line in split_preview:
                        st.markdown(line)

        client = anthropic.Anthropic(api_key=api_key)

        results = []
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        for i, row in employee_df.iterrows():
            name = str(row["Name"]).strip()
            level = str(row["Level"]).strip()
            self_rating = row["Self Rating"]
            manager_rating = row["Manager Rating"]
            rating_gap = abs(float(self_rating) - float(manager_rating))

            status_text.text(f"Analyzing {name} ({i + 1} of {len(employee_df)})...")

            self_review_text    = find_review_for_employee(name, self_reviews) or "No self review document provided."
            manager_review_text = find_review_for_employee(name, manager_reviews) or "No manager review document provided."

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
                    "primary_concern": f"Could not complete AI analysis ({str(e)[:80]}). Rating gap: {rating_gap:.1f} points.",
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

        status_text.text("✅ Analysis complete!")
        progress_bar.empty()

        results_df = pd.DataFrame(results).sort_values("Priority Score", ascending=False).reset_index(drop=True)
        st.session_state["results"] = results_df

    # ── Results ────────────────────────────────────────
    if "results" in st.session_state:
        results_df = st.session_state["results"]

        st.divider()
        st.header("📊 Calibration Results")

        total = len(results_df)
        high_count   = len(results_df[results_df["Priority Score"] >= 7])
        medium_count = len(results_df[(results_df["Priority Score"] >= 4) & (results_df["Priority Score"] < 7)])
        low_count    = len(results_df[results_df["Priority Score"] < 4])
        gap_count    = len(results_df[results_df["rating_gap_concern"] == True])
        narrative_count = len(results_df[
            results_df["narrative_rating_mismatch"] | results_df["self_manager_conflict"]
        ])

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Employees", total)
        m2.metric("🔴 High Priority", high_count)
        m3.metric("🟡 Medium Priority", medium_count)
        m4.metric("Rating Gap Flags", gap_count)
        m5.metric("Narrative Flags", narrative_count)

        # High priority
        st.subheader("🔴 High Priority — Discuss First")
        high = results_df[results_df["Priority Score"] >= 7]
        if len(high) == 0:
            st.success("No high-priority employees flagged — great sign!")
        for _, row in high.iterrows():
            header = (
                f"**{row['Name']}** ({row['Level']}) — "
                f"Score: {row['Priority Score']}/10 &nbsp;|&nbsp; "
                f"Self: {row['Self Rating']} → Manager: {row['Manager Rating']} "
                f"(Gap: {row['Gap']:.1f})"
            )
            with st.expander(header, expanded=True):
                st.markdown(f"**Primary Concern:** {row['Primary Concern']}")
                badge_cols = st.columns(3)
                if row["rating_gap_concern"]:
                    badge_cols[0].error("⚠️ Rating Gap")
                if row["narrative_rating_mismatch"]:
                    badge_cols[1].warning("📄 Narrative ≠ Rating")
                if row["self_manager_conflict"]:
                    badge_cols[2].warning("🔀 Self ≠ Manager Narrative")
                if row["Flags"]:
                    st.markdown("**Specific Flags:**")
                    for flag in row["Flags"]:
                        st.markdown(f"- {flag}")
                if row["Discussion Points"]:
                    st.markdown("**Suggested Discussion Points:**")
                    for pt in row["Discussion Points"]:
                        st.markdown(f"- {pt}")

        # Medium priority
        st.subheader("🟡 Medium Priority — Time Permitting")
        medium = results_df[(results_df["Priority Score"] >= 4) & (results_df["Priority Score"] < 7)]
        if len(medium) == 0:
            st.info("No medium-priority employees.")
        for _, row in medium.iterrows():
            header = (
                f"**{row['Name']}** ({row['Level']}) — "
                f"Score: {row['Priority Score']}/10 &nbsp;|&nbsp; "
                f"Self: {row['Self Rating']} → Manager: {row['Manager Rating']} "
                f"(Gap: {row['Gap']:.1f})"
            )
            with st.expander(header):
                st.markdown(f"**Primary Concern:** {row['Primary Concern']}")
                if row["Flags"]:
                    for flag in row["Flags"]:
                        st.markdown(f"- {flag}")

        # Low priority
        st.subheader("🟢 Low Priority — Likely No Discussion Needed")
        low = results_df[results_df["Priority Score"] < 4]
        if len(low) > 0:
            st.dataframe(
                low[["Name", "Level", "Self Rating", "Manager Rating", "Gap", "Primary Concern"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("All employees were flagged as medium or high priority.")

        # Export
        st.divider()
        st.subheader("📥 Export Results")
        export_df = results_df[[
            "Name", "Level", "Self Rating", "Manager Rating", "Gap",
            "Priority Score", "Primary Concern"
        ]].copy()
        st.download_button(
            label="Download Results as CSV",
            data=export_df.to_csv(index=False),
            file_name="calibration_results.csv",
            mime="text/csv",
        )


# ═════════════════════════════════════════════
# TAB 2 — FILE LIBRARY
# ═════════════════════════════════════════════
with tab_library:

    st.title("📁 File Library")
    st.markdown(
        "Save career ladders and rating scales here so they're permanently available "
        "to everyone using this tool — no re-uploading needed each session."
    )

    token, owner, repo = get_github_config()

    if not token:
        # ── Not configured ──
        st.info(
            "**The File Library isn't set up yet.**\n\n"
            "To enable it, add two secrets to your Streamlit app:\n\n"
            "```\nGITHUB_TOKEN = \"ghp_your_token_here\"\n"
            "GITHUB_REPO  = \"your-username/calibration-tool\"\n```\n\n"
            "See **HOW_TO_DEPLOY.md** in your folder for step-by-step instructions."
        )
        st.markdown("---")
        st.markdown(
            "**In the meantime:** you can still upload career ladders and rating scales "
            "directly in Step 1 of the Calibration tab each time you run a session."
        )

    else:
        # ── Configured — show library management UI ──
        st.success(f"Connected to **{owner}/{repo}** ✓")
        st.markdown(
            "Upload a file below and click **Save to Library**. "
            "It'll appear in the Step 1 dropdown for everyone within about 60 seconds."
        )

        st.divider()

        col_ladders, col_scales = st.columns(2)

        with col_ladders:
            file_library_section(
                label="Career Ladders",
                folder="career_ladders",
                token=token,
                owner=owner,
                repo=repo,
            )

        with col_scales:
            file_library_section(
                label="Rating Scales",
                folder="rating_scales",
                token=token,
                owner=owner,
                repo=repo,
            )

        st.divider()
        st.caption(
            "Files are stored directly in your GitHub repo. "
            "Streamlit automatically redeploys when the repo changes, "
            "so new files appear in the dropdown within ~60 seconds of saving."
        )
