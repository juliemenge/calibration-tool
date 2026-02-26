import streamlit as st
import anthropic
import pdfplumber
import pandas as pd
import json
from io import BytesIO

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Calibration Tool",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Performance Review Calibration Tool")
st.markdown(
    "Upload your materials below and the tool will identify who most needs discussion in your calibration session."
)

# ─────────────────────────────────────────────
# Sidebar: API key
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    # Check if an API key was pre-configured (for deployment where the owner embeds their key)
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

# ─────────────────────────────────────────────
# Helper: extract text from a PDF upload
# ─────────────────────────────────────────────
def extract_pdf_text(uploaded_file):
    """Extract all text from an uploaded PDF file."""
    text = ""
    try:
        uploaded_file.seek(0)  # reset pointer in case file was read before
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
    # "Last, First" format (Lattice default)
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        last, first = parts[0], parts[1]
    else:
        tokens = name.split()
        first = tokens[0] if tokens else ""
        last  = tokens[-1] if len(tokens) > 1 else ""
    # Strip punctuation and lowercase
    clean = lambda s: re.sub(r"[^a-z]", "", s.lower())
    return clean(first), clean(last)


def find_review_for_employee(name, pdf_dict):
    """
    Match an employee name to the right file in pdf_dict {filename: text}.

    Handles:
      - "Last, First" CSV names   (Lattice export)
      - "First Last"  CSV names
      - Filenames containing email prefix (justin@helpscout.com_...)
      - Hyphenated names in filenames (Justin-Wolfe)
      - Names appearing in any order in the filename
    """
    first, last = parse_name(name)
    if not first and not last:
        return None

    fn_lower = {fn: fn.lower() for fn in pdf_dict}

    # Build candidate strings to search for in filenames
    candidates = []
    if first and last:
        candidates += [
            f"{first}-{last}",    # justin-wolfe
            f"{last}-{first}",    # wolfe-justin
            f"{first} {last}",    # justin wolfe
            f"{last} {first}",    # wolfe justin
            f"{last}_{first}",    # wolfe_justin
            f"{first}_{last}",    # justin_wolfe
        ]

    # 1. Try each combined candidate
    for fn, fln in fn_lower.items():
        for cand in candidates:
            if cand in fln:
                return pdf_dict[fn]

    # 2. Both first AND last appear anywhere in filename (handles middle names,
    #    email prefixes, extra tokens, etc.)
    if first and last:
        matches = [
            fn for fn, fln in fn_lower.items()
            if first in fln and last in fln
        ]
        if len(matches) == 1:
            return pdf_dict[matches[0]]
        if len(matches) > 1:
            return pdf_dict[matches[0]]  # take first hit

    # 3. Last name only — unique match fallback
    if last:
        matches = [fn for fn, fln in fn_lower.items() if last in fln]
        if len(matches) == 1:
            return pdf_dict[matches[0]]

    return None


def split_combined_review(uploaded_file):
    """
    Extract and split a combined review packet PDF into manager review text
    and self review text, based on section header markers in the document.

    Strategy: scan page by page. A page that contains BOTH 'manager review'
    and 'self review' is a TOC/cover page — skip it. A page with only one
    marker starts that section; subsequent pages with no marker continue it.

    Returns (manager_text, self_text) — either may be empty string if not found.
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
                    # Cover / TOC page — skip
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
                # else: closing/acknowledgement page — skip
    except Exception as e:
        return f"[Error reading file: {e}]", ""

    return "\n\n".join(manager_pages).strip(), "\n\n".join(self_pages).strip()


# ─────────────────────────────────────────────
# Step 1: Context documents
# ─────────────────────────────────────────────
st.divider()
st.header("Step 1 — Context Documents")
st.markdown(
    "These teach the tool what your company's career ladder and rating definitions actually mean. "
    "Upload PDFs or plain text files."
)

col1, col2 = st.columns(2)
with col1:
    career_ladder_file = st.file_uploader(
        "📋 Career Ladder",
        type=["pdf", "txt"],
        help="Your engineering (or other) career ladder with level definitions."
    )
with col2:
    rating_scale_file = st.file_uploader(
        "⭐ Rating Scale & Definitions",
        type=["pdf", "txt"],
        help="The rating scale used in reviews, with written definitions for each level."
    )

# ─────────────────────────────────────────────
# Step 2: Employee data CSV
# ─────────────────────────────────────────────
st.divider()
st.header("Step 2 — Employee Data")
st.markdown(
    "Upload a CSV with one row per employee. Required columns: **Name**, **Level**, "
    "**Self Rating**, **Manager Rating**."
)

# Downloadable template
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
            employee_data_file.seek(0)  # reset for later read
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        employee_data_file = None

# ─────────────────────────────────────────────
# Step 3: Review PDFs
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# Analysis button
# ─────────────────────────────────────────────
st.divider()

ready = bool(api_key and career_ladder_file and rating_scale_file and employee_data_file)

if not ready:
    missing_items = []
    if not api_key:
        missing_items.append("Anthropic API key")
    if not career_ladder_file:
        missing_items.append("Career Ladder")
    if not rating_scale_file:
        missing_items.append("Rating Scale")
    if not employee_data_file:
        missing_items.append("Employee Data CSV")
    st.info(f"Still needed to run: {', '.join(missing_items)}")

run_button = st.button("🚀 Run Calibration Analysis", type="primary", disabled=not ready)

if run_button:
    # ── Extract context documents ──
    with st.spinner("Reading context documents..."):
        career_ladder_text = read_uploaded_file(career_ladder_file)
        rating_scale_text = read_uploaded_file(rating_scale_file)

    # ── Extract employee data ──
    employee_df = pd.read_csv(employee_data_file)

    # ── Extract and split combined review packets ──
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

    # ── Run LLM analysis for each employee ──
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

        self_review_text = find_review_for_employee(name, self_reviews) or "No self review document provided."
        manager_review_text = find_review_for_employee(name, manager_reviews) or "No manager review document provided."

        prompt = f"""You are an expert HR consultant helping a team prepare for a performance calibration session.
Your job is to analyze one employee's review data and determine how important they are to discuss,
and why. Be specific and grounded in the actual text provided.

━━━ CAREER LADDER ━━━
{career_ladder_text[:4000]}

━━━ RATING SCALE DEFINITIONS ━━━
{rating_scale_text[:2000]}

━━━ EMPLOYEE DETAILS ━━━
Name: {name}
Level: {level}
Self Rating: {self_rating}
Manager Rating: {manager_rating}
Rating Gap: {rating_gap:.1f} points

━━━ SELF REVIEW TEXT ━━━
{self_review_text[:2500]}

━━━ MANAGER REVIEW TEXT ━━━
{manager_review_text[:2500]}

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
            # Strip markdown code fences if present
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            analysis = json.loads(raw)

        except Exception as e:
            # Fallback: use numeric gap only
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

# ─────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────
if "results" in st.session_state:
    results_df = st.session_state["results"]

    st.divider()
    st.header("📊 Calibration Results")

    # Summary metrics
    total = len(results_df)
    high_count = len(results_df[results_df["Priority Score"] >= 7])
    medium_count = len(results_df[(results_df["Priority Score"] >= 4) & (results_df["Priority Score"] < 7)])
    low_count = len(results_df[results_df["Priority Score"] < 4])
    gap_count = len(results_df[results_df["rating_gap_concern"] == True])
    narrative_count = len(results_df[
        results_df["narrative_rating_mismatch"] | results_df["self_manager_conflict"]
    ])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Employees", total)
    m2.metric("🔴 High Priority", high_count)
    m3.metric("🟡 Medium Priority", medium_count)
    m4.metric("Rating Gap Flags", gap_count)
    m5.metric("Narrative Flags", narrative_count)

    # ── HIGH PRIORITY ──
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

    # ── MEDIUM PRIORITY ──
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

    # ── LOW PRIORITY ──
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

    # ── Export ──
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
