"""
app.py — TenderAudit: AI-Powered Government Tender Eligibility Evaluator
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

from modules.document_processor import (
    extract_text_from_pdf, extract_text_from_image, truncate_text
)
from modules.llm_engine import (
    get_groq_client, extract_criteria_from_tender,
    evaluate_bidder, compute_overall_status, compute_average_confidence
)
from modules.pdf_exporter import generate_report

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
load_dotenv()

st.set_page_config(
    page_title="TenderAudit",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main palette */
    :root {
        --blue-dark: #1a2744;
        --blue-mid: #2c3e6b;
        --blue-accent: #3b6fd4;
        --green: #1a7a4a;
        --red: #c0392b;
        --orange: #d4800a;
        --bg-light: #f4f6fb;
        --border: #d0d8e8;
    }

    /* Page background */
    .stApp { background-color: #f0f3fa; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2744 0%, #2c3e6b 100%) !important;
    }
    [data-testid="stSidebar"] * { color: #e8edf8 !important; }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 { color: #ffffff !important; }
    [data-testid="stSidebar"] hr { border-color: #3b5080 !important; }

    /* Header banner */
    .ta-header {
        background: linear-gradient(135deg, #1a2744 0%, #2c3e6b 60%, #3b6fd4 100%);
        color: white;
        padding: 1.4rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }
    .ta-header h1 { margin: 0; font-size: 1.8rem; letter-spacing: 0.03em; }
    .ta-header p { margin: 0.2rem 0 0; opacity: 0.75; font-size: 0.9rem; }

    /* Section headers */
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a2744;
        border-left: 4px solid #3b6fd4;
        padding-left: 0.7rem;
        margin: 1.2rem 0 0.8rem;
    }

    /* Status badges */
    .badge-eligible {
        background: #d4edda; color: #155724;
        padding: 3px 10px; border-radius: 20px;
        font-weight: 700; font-size: 0.82rem;
        display: inline-block;
    }
    .badge-noteligible {
        background: #f8d7da; color: #721c24;
        padding: 3px 10px; border-radius: 20px;
        font-weight: 700; font-size: 0.82rem;
        display: inline-block;
    }
    .badge-review {
        background: #fff3cd; color: #856404;
        padding: 3px 10px; border-radius: 20px;
        font-weight: 700; font-size: 0.82rem;
        display: inline-block;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .metric-card .val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #1a2744;
    }
    .metric-card .lbl {
        font-size: 0.78rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Bidder card */
    .bidder-card {
        background: white;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.8rem;
        cursor: pointer;
        transition: box-shadow 0.2s;
    }
    .bidder-card:hover { box-shadow: 0 4px 16px rgba(59,111,212,0.15); }
    .bidder-card.selected { border: 2px solid #3b6fd4; }

    /* Info box */
    .info-box {
        background: #eef2ff;
        border-left: 4px solid #3b6fd4;
        padding: 0.8rem 1rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.88rem;
        color: #2c3e6b;
        margin-bottom: 1rem;
    }

    /* Override banner */
    .override-banner {
        background: #fff8e1;
        border-left: 4px solid #f59e0b;
        padding: 0.5rem 1rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.83rem;
        color: #78530a;
        margin: 0.3rem 0;
    }

    /* Step number */
    .step-num {
        display: inline-block;
        background: #3b6fd4;
        color: white;
        border-radius: 50%;
        width: 26px; height: 26px;
        text-align: center;
        line-height: 26px;
        font-weight: 700;
        font-size: 0.85rem;
        margin-right: 8px;
    }
    /* Fix white text on white background */
    .metric-card .val { color: #1a2744 !important; }
    .metric-card .lbl { color: #444444 !important; }
    .stDataFrame { color: #1a2744 !important; }

    /* Fix badges - light background with dark text */
    .badge-eligible { 
        background: #d4edda !important; 
        color: #155724 !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
    }
    .badge-noteligible { 
        background: #f8d7da !important; 
        color: #721c24 !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
    }
    .badge-review { 
        background: #fff3cd !important; 
        color: #856404 !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
    }

    
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Button style */
    .stButton > button {
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"] {
        background: #3b6fd4;
        border: none;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "api_key": st.secrets.get("GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", ""),
        "stage": "setup",           # setup → tender → bidders → evaluation → results
        "tender_text": "",
        "tender_name": "Untitled Tender",
        "criteria": [],
        "bidder_docs": {},          # {bidder_name: {text, pages, filename}}
        "evaluations": {},          # {bidder_name: {overall_status, avg_confidence, results}}
        "selected_bidder": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def status_badge(status: str) -> str:
    s = status.lower()
    if "eligible" in s and "not" not in s:
        return f'<span class="badge-eligible">✓ {status}</span>'
    if "not eligible" in s or "fail" in s:
        return f'<span class="badge-noteligible">✗ {status}</span>'
    return f'<span class="badge-review">⚑ {status}</span>'


def criterion_status_icon(status: str) -> str:
    s = status.lower()
    if s == "pass":
        return "✅ Pass"
    if s == "fail":
        return "❌ Fail"
    return "⚠️ Needs Review"


def get_groq(api_key: str = None):
    key = api_key or st.session_state.api_key
    # Try secrets if no key found
    if not key:
        try:
            key = st.secrets.get("GROQ_API_KEY", "")
        except Exception:
            pass
    return get_groq_client(key)


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🏛️ TenderAudit")
        st.markdown("*AI-powered eligibility evaluation*")
        st.markdown("---")

        # API Key
        st.markdown("### 🔑 Groq API Key")
        api_input = st.text_input(
            "Enter your Groq API Key",
            value=st.session_state.api_key,
            type="password",
            placeholder="gsk_...",
            label_visibility="collapsed"
        )
        if api_input:
            st.session_state.api_key = api_input
        if st.session_state.api_key:
            st.success("API key set ✓")
        else:
            st.warning("API key required")
            st.markdown("[Get free key at console.groq.com](https://console.groq.com)")

        st.markdown("---")

        # Navigation / Progress
        st.markdown("### 📋 Progress")
        stages = [
            ("tender", "1. Upload Tender"),
            ("bidders", "2. Upload Bidders"),
            ("evaluation", "3. Run Evaluation"),
            ("results", "4. View Results"),
        ]
        stage_order = ["setup", "tender", "bidders", "evaluation", "results"]
        current_idx = stage_order.index(st.session_state.stage) if st.session_state.stage in stage_order else 0

        for i, (key, label) in enumerate(stages):
            idx = i + 1
            if stage_order.index(key) < current_idx:
                st.markdown(f"✅ {label}")
            elif stage_order.index(key) == current_idx:
                st.markdown(f"▶️ **{label}**")
            else:
                st.markdown(f"○ {label}")

        st.markdown("---")

        # Quick stats
        if st.session_state.evaluations:
            evals = st.session_state.evaluations
            eligible = sum(1 for e in evals.values()
                          if (e.get("override_overall_status") or e.get("overall_status")) == "Eligible")
            review = sum(1 for e in evals.values()
                        if (e.get("override_overall_status") or e.get("overall_status")) == "Needs Review")
            not_elig = len(evals) - eligible - review
            st.markdown("### 📊 Quick Stats")
            st.markdown(f"🟢 **{eligible}** Eligible")
            st.markdown(f"🟡 **{review}** Needs Review")
            st.markdown(f"🔴 **{not_elig}** Not Eligible")

        st.markdown("---")

        # Reset
        if st.button("🔄 Start New Evaluation", use_container_width=True):
            for key in ["tender_text", "tender_name", "criteria",
                        "bidder_docs", "evaluations", "selected_bidder"]:
                st.session_state[key] = {} if key in ["bidder_docs", "evaluations"] else (
                    [] if key == "criteria" else ("" if key != "selected_bidder" else None)
                )
            st.session_state.stage = "tender"
            st.rerun()


# ─────────────────────────────────────────────────────────────
# PAGE: TENDER UPLOAD
# ─────────────────────────────────────────────────────────────
def page_tender():
    st.markdown("""
    <div class="ta-header">
        <h1>🏛️ TenderAudit</h1>
        <p>Semi-automatic, explainable AI system for government tender eligibility evaluation</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="info-box">📌 <b>Step 1:</b> Upload the tender document. The AI will automatically extract eligibility criteria which you can review and edit before proceeding.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        tender_name = st.text_input(
            "Tender Name / Reference Number",
            value=st.session_state.tender_name,
            placeholder="e.g., TENDER/2024-25/IT/0042"
        )
        st.session_state.tender_name = tender_name

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)

    tender_file = st.file_uploader(
        "Upload Tender Document (PDF or Image)",
        type=["pdf", "png", "jpg", "jpeg", "tiff"],
        help="Supports both digital and scanned PDFs. Images will be OCR processed."
    )

    if tender_file:
        if st.button("📄 Extract Text & Identify Criteria", type="primary", use_container_width=True):
            with st.spinner("Extracting text from document..."):
                file_bytes = tender_file.read()
                fname = tender_file.name.lower()

                if fname.endswith(".pdf"):
                    result = extract_text_from_pdf(file_bytes, tender_file.name)
                else:
                    result = extract_text_from_image(file_bytes, tender_file.name)

                if result.get("error"):
                    st.error(f"Extraction error: {result['error']}")
                    return

                tender_text = result["full_text"]
                if not tender_text.strip():
                    st.error("Could not extract text. Please check the document.")
                    return

                st.session_state.tender_text = tender_text

            with st.spinner("AI is identifying eligibility criteria..."):
                if not st.session_state.api_key:
                    st.error("Please enter your Groq API key in the sidebar.")
                    return
                try:
                    client = get_groq()
                    truncated = truncate_text(tender_text, 10000)
                    criteria = extract_criteria_from_tender(client, truncated)
                    if not criteria:
                        st.warning("No criteria extracted. You can add them manually below.")
                        criteria = []
                    st.session_state.criteria = criteria
                    st.session_state.stage = "tender"
                    st.success(f"✅ Extracted {len(criteria)} eligibility criteria!")
                except Exception as e:
                    st.error(f"LLM Error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                    return

    # Show / edit criteria
    if st.session_state.criteria or st.session_state.tender_text:
        st.markdown('<div class="section-header">📋 Eligibility Criteria — Review & Edit</div>', unsafe_allow_html=True)
        st.markdown("You can edit any cell, add rows, or delete rows before proceeding.")

        df = pd.DataFrame(
            st.session_state.criteria if st.session_state.criteria else [],
            columns=["criterion_name", "type", "required_value", "unit", "description"]
        )
        # Rename for display
        df.columns = ["Criterion Name", "Type", "Required Value", "Unit", "Description"]

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Criterion Name": st.column_config.TextColumn("Criterion Name", width="medium"),
                "Type": st.column_config.SelectboxColumn(
                    "Type", options=["Financial", "Technical", "Compliance"], width="small"
                ),
                "Required Value": st.column_config.TextColumn("Required Value", width="small"),
                "Unit": st.column_config.TextColumn("Unit", width="small"),
                "Description": st.column_config.TextColumn("Description", width="large"),
            },
            key="criteria_editor"
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💾 Save Criteria & Continue →", type="primary", use_container_width=True):
                # Convert back
                records = edited_df.rename(columns={
                    "Criterion Name": "criterion_name",
                    "Type": "type",
                    "Required Value": "required_value",
                    "Unit": "unit",
                    "Description": "description"
                }).to_dict("records")
                # Filter empty rows
                records = [r for r in records if r.get("criterion_name", "").strip()]
                if not records:
                    st.error("Please add at least one criterion.")
                    return
                st.session_state.criteria = records
                st.session_state.stage = "bidders"
                st.success(f"Saved {len(records)} criteria. Proceeding to bidder upload...")
                st.rerun()

        with col2:
            if st.session_state.tender_text:
                with st.expander("👁️ View Extracted Tender Text"):
                    st.text_area("Raw Text", st.session_state.tender_text[:5000] + "..." if len(st.session_state.tender_text) > 5000 else st.session_state.tender_text, height=300, disabled=True)


# ─────────────────────────────────────────────────────────────
# PAGE: BIDDER UPLOAD
# ─────────────────────────────────────────────────────────────
def page_bidders():
    st.markdown('<div class="section-header">📁 Step 2: Upload Bidder Documents</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Upload documents for each bidder. Group files by bidder using the name field. Supports PDFs and scanned images. Aim for 3–5 bidders for best demo results.</div>', unsafe_allow_html=True)

    # Show existing bidders
    if st.session_state.bidder_docs:
        st.markdown("**Uploaded Bidders:**")
        cols = st.columns(min(len(st.session_state.bidder_docs), 4))
        for i, (name, data) in enumerate(st.session_state.bidder_docs.items()):
            with cols[i % 4]:
                st.markdown(f"""
                <div style="background:white;border:1px solid #d0d8e8;border-radius:8px;padding:0.8rem;text-align:center;margin-bottom:0.5rem;">
                    <div style="font-size:1.5rem">📂</div>
                    <div style="font-weight:700;font-size:0.9rem;color:#1a2744">{name}</div>
                    <div style="font-size:0.75rem;color:#666">{data.get('total_pages',0)} pages extracted</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Upload form
    with st.form("bidder_upload_form", clear_on_submit=True):
        st.markdown("**Add a Bidder**")
        col1, col2 = st.columns([1, 2])
        with col1:
            bidder_name = st.text_input("Bidder / Company Name", placeholder="e.g., Sunrise Technologies Pvt Ltd")
        with col2:
            uploaded_files = st.file_uploader(
                "Upload Documents (PDF / Images)",
                type=["pdf", "png", "jpg", "jpeg", "tiff"],
                accept_multiple_files=True,
                help="Upload all documents for this bidder: financial statements, certifications, experience certificates, etc."
            )

        submitted = st.form_submit_button("➕ Add Bidder", type="primary")

        if submitted:
            if not bidder_name.strip():
                st.error("Please enter a bidder name.")
            elif not uploaded_files:
                st.error("Please upload at least one document.")
            else:
                combined_text = ""
                total_pages = 0
                all_pages = []

                with st.spinner(f"Processing documents for {bidder_name}..."):
                    for f in uploaded_files:
                        file_bytes = f.read()
                        fname = f.name.lower()
                        if fname.endswith(".pdf"):
                            result = extract_text_from_pdf(file_bytes, f.name)
                        else:
                            result = extract_text_from_image(file_bytes, f.name)

                        if result.get("error"):
                            st.warning(f"Warning: {f.name} — {result['error']}")
                        else:
                            combined_text += f"\n\n[File: {f.name}]\n" + result["full_text"]
                            total_pages += result.get("total_pages", 0)
                            for p in result.get("pages", []):
                                all_pages.append({**p, "filename": f.name})

                st.session_state.bidder_docs[bidder_name.strip()] = {
                    "text": combined_text,
                    "total_pages": total_pages,
                    "pages": all_pages,
                    "filenames": [f.name for f in uploaded_files]
                }
                st.success(f"✅ Added {bidder_name} ({total_pages} pages processed)")
                st.rerun()

    # Remove bidder
    if st.session_state.bidder_docs:
        st.markdown("---")
        remove_name = st.selectbox(
            "Remove a bidder",
            ["— select —"] + list(st.session_state.bidder_docs.keys())
        )
        if remove_name != "— select —":
            if st.button(f"🗑️ Remove {remove_name}"):
                del st.session_state.bidder_docs[remove_name]
                if remove_name in st.session_state.evaluations:
                    del st.session_state.evaluations[remove_name]
                st.rerun()

    # Proceed
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back to Tender", use_container_width=True):
            st.session_state.stage = "tender"
            st.rerun()
    with col2:
        n = len(st.session_state.bidder_docs)
        if n > 0:
            if st.button(f"▶ Run Evaluation ({n} bidders) →", type="primary", use_container_width=True):
                st.session_state.stage = "evaluation"
                st.rerun()
        else:
            st.info("Upload at least 1 bidder to continue.")


# ─────────────────────────────────────────────────────────────
# PAGE: EVALUATION
# ─────────────────────────────────────────────────────────────
def page_evaluation():
    st.markdown('<div class="section-header">⚙️ Step 3: AI Evaluation</div>', unsafe_allow_html=True)

    bidder_names = list(st.session_state.bidder_docs.keys())
    already_done = list(st.session_state.evaluations.keys())
    pending = [b for b in bidder_names if b not in already_done]

    if not st.session_state.api_key:
        st.error("Please enter your Groq API key in the sidebar before running evaluation.")
        return

    st.markdown(f"""
    <div class="info-box">
        Ready to evaluate <b>{len(bidder_names)}</b> bidder(s) against <b>{len(st.session_state.criteria)}</b> eligibility criteria using Groq Llama 3.1.
        {f'<br>✅ Already evaluated: {", ".join(already_done)}' if already_done else ''}
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        run_all = st.button("🚀 Run Full Evaluation", type="primary", use_container_width=True)
    with col2:
        if already_done:
            run_pending = st.button(f"▶ Evaluate Pending ({len(pending)})", use_container_width=True)
        else:
            run_pending = False

    targets = []
    if run_all:
        targets = bidder_names
        st.session_state.evaluations = {}  # reset
    elif run_pending:
        targets = pending

    if targets:
        client = get_groq()
        progress = st.progress(0)
        status_text = st.empty()

        for i, bidder_name in enumerate(targets):
            status_text.markdown(f"**Evaluating:** {bidder_name} ({i+1}/{len(targets)})")
            try:
                bidder_data = st.session_state.bidder_docs[bidder_name]
                bidder_text = truncate_text(bidder_data["text"], 10000)

                results = evaluate_bidder(
                    client,
                    bidder_name,
                    bidder_text,
                    st.session_state.criteria
                )
                overall = compute_overall_status(results)
                conf = compute_average_confidence(results)

                st.session_state.evaluations[bidder_name] = {
                    "bidder_name": bidder_name,
                    "overall_status": overall,
                    "avg_confidence": conf,
                    "results": results,
                    "override_overall_status": None
                }
            except Exception as e:
                st.error(f"Error evaluating {bidder_name}: {str(e)}")

            progress.progress((i + 1) / len(targets))

        status_text.markdown("✅ **Evaluation complete!**")
        st.session_state.stage = "results"
        st.rerun()

    # Manual skip to results
    if st.session_state.evaluations:
        st.markdown("---")
        if st.button("📊 View Results →", type="primary"):
            st.session_state.stage = "results"
            st.rerun()

    col1, _ = st.columns([1, 3])
    with col1:
        if st.button("← Back to Bidders"):
            st.session_state.stage = "bidders"
            st.rerun()


# ─────────────────────────────────────────────────────────────
# PAGE: RESULTS — DASHBOARD
# ─────────────────────────────────────────────────────────────
def page_results():
    st.markdown('<div class="section-header">📊 Evaluation Results Dashboard</div>', unsafe_allow_html=True)

    evals = st.session_state.evaluations
    if not evals:
        st.warning("No evaluation results yet. Please run the evaluation first.")
        if st.button("← Go to Evaluation"):
            st.session_state.stage = "evaluation"
            st.rerun()
        return

    # ── Summary Metrics ──────────────────────────────────────────────────
    total = len(evals)
    eligible = sum(1 for e in evals.values()
                  if (e.get("override_overall_status") or e.get("overall_status")) == "Eligible")
    review = sum(1 for e in evals.values()
                if (e.get("override_overall_status") or e.get("overall_status")) == "Needs Review")
    not_elig = total - eligible - review
    avg_conf = sum(e.get("avg_confidence", 0) for e in evals.values()) / total if total else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    for col, val, lbl, color in [
        (m1, total, "Total Bidders", "#1a2744"),
        (m2, eligible, "Eligible", "#1a7a4a"),
        (m3, review, "Needs Review", "#d4800a"),
        (m4, not_elig, "Not Eligible", "#c0392b"),
        (m5, f"{avg_conf:.0f}%", "Avg Confidence", "#3b6fd4"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="val" style="color:{color}">{val}</div>
                <div class="lbl">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Summary Table ────────────────────────────────────────────────────
    st.markdown("**Click a row to view detailed evaluation ↓**")

    summary_rows = []
    for name, e in evals.items():
        results = e.get("results", [])
        eff_status = e.get("override_overall_status") or e.get("overall_status", "Needs Review")
        passed = sum(1 for r in results if (r.get("override_status") or r.get("status")) == "Pass")
        failed = sum(1 for r in results if (r.get("override_status") or r.get("status")) == "Fail")
        flagged = len(results) - passed - failed

        summary_rows.append({
            "Bidder Name": name,
            "Overall Status": eff_status,
            "Confidence": f"{e.get('avg_confidence', 0):.0f}%",
            "✅ Passed": passed,
            "⚠️ Flagged": flagged,
            "❌ Failed": failed,
        })

    df_summary = pd.DataFrame(summary_rows)

    def highlight_status(val):
        if val == "Eligible":
            return "color: #1a7a4a; font-weight: bold"
        if val == "Not Eligible":
            return "color: #c0392b; font-weight: bold"
        if val == "Needs Review":
            return "color: #d4800a; font-weight: bold"
        return ""

    styled = df_summary.style.map(highlight_status, subset=["Overall Status"])
    st.dataframe(styled, use_container_width=True, height=200)

    # Bidder selector
    st.markdown('<div class="section-header">🔍 Detailed Bidder View</div>', unsafe_allow_html=True)

    bidder_options = list(evals.keys())
    selected = st.selectbox(
        "Select bidder to inspect",
        bidder_options,
        index=bidder_options.index(st.session_state.selected_bidder)
        if st.session_state.selected_bidder in bidder_options else 0
    )
    st.session_state.selected_bidder = selected

    render_bidder_detail(selected, evals[selected])

    # ── Export ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-header">📥 Export Report</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("📄 Generate PDF Report", type="primary", use_container_width=True):
            with st.spinner("Generating PDF..."):
                try:
                    bidders_list = list(evals.values())
                    pdf_bytes = generate_report(
                        tender_name=st.session_state.tender_name,
                        criteria=st.session_state.criteria,
                        bidders=bidders_list
                    )
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"TenderAudit_Report_{st.session_state.tender_name[:30]}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"PDF generation error: {str(e)}")
    with col2:
        st.markdown("""
        <div class="info-box">
            The PDF report includes the executive summary, all eligibility criteria, per-bidder detailed evaluations, officer overrides, and full audit trail.
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# DETAILED BIDDER VIEW
# ─────────────────────────────────────────────────────────────
def render_bidder_detail(bidder_name: str, evaluation: dict):
    results = evaluation.get("results", [])
    overall = evaluation.get("override_overall_status") or evaluation.get("overall_status", "Needs Review")
    conf = evaluation.get("avg_confidence", 0)

    # Header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"### {bidder_name}")
    with col2:
        st.markdown(f"**Overall Status:**<br>{status_badge(overall)}", unsafe_allow_html=True)
    with col3:
        st.markdown(f"**Avg Confidence:**<br><span style='font-size:1.3rem;font-weight:800;color:#1a2744'>{conf:.0f}%</span>", unsafe_allow_html=True)

    # Override overall status
    if evaluation.get("override_overall_status"):
        st.markdown(f'<div class="override-banner">⚑ Officer Override: Overall status set to <b>{evaluation["override_overall_status"]}</b></div>', unsafe_allow_html=True)

    with st.expander("✏️ Override Overall Bidder Status"):
        new_overall = st.radio(
            "Change overall status to:",
            ["Eligible", "Needs Review", "Not Eligible"],
            index=["Eligible", "Needs Review", "Not Eligible"].index(overall) if overall in ["Eligible", "Needs Review", "Not Eligible"] else 1,
            horizontal=True,
            key=f"override_overall_{bidder_name}"
        )
        if st.button("Apply Overall Override", key=f"apply_overall_{bidder_name}"):
            st.session_state.evaluations[bidder_name]["override_overall_status"] = new_overall
            st.success(f"Overall status overridden to: {new_overall}")
            st.rerun()

    st.markdown("---")

    # Per-criterion detail table
    st.markdown("**Criterion-by-Criterion Evaluation:**")

    criteria_map = {c.get("criterion_name", "").lower(): c for c in st.session_state.criteria}

    for i, r in enumerate(results):
        cname = r.get("criterion_name", f"Criterion {i+1}")
        crit = criteria_map.get(cname.lower(), {})
        req_val = f"{crit.get('required_value', 'N/A')} {crit.get('unit', '')}".strip()
        extracted = r.get("extracted_value", "Not Found")
        page = r.get("source_page", 0)
        conf_pct = r.get("confidence", 0)
        reasoning = r.get("reasoning", "")
        eff_status = r.get("override_status") or r.get("status", "Needs Review")

        # Card per criterion
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2.5, 2, 2, 1, 2])
            with c1:
                st.markdown(f"**{cname}**")
                st.caption(f"_{crit.get('type', '')}_ · {crit.get('description', '')[:80]}...")
            with c2:
                st.markdown(f"**Required:** `{req_val}`")
                st.markdown(f"**Extracted:** `{extracted}`")
            with c3:
                src = f"Page {page}" if page and page > 0 else "Not located"
                st.markdown(f"**Source:** {src}")
                st.caption(f"_{reasoning[:100]}_")
            with c4:
                conf_color = "#1a7a4a" if conf_pct >= 75 else ("#d4800a" if conf_pct >= 40 else "#c0392b")
                st.markdown(f"<div style='font-size:1.4rem;font-weight:800;color:{conf_color};text-align:center'>{conf_pct}%</div>", unsafe_allow_html=True)
                st.caption("confidence")
            with c5:
                st.markdown(criterion_status_icon(eff_status))
                if r.get("override_status"):
                    st.caption(f"⚑ Overridden")

            # Override controls (collapsed by default)
            with st.expander(f"✏️ Override '{cname}' status"):
                override_val = st.radio(
                    "Set status:",
                    ["Pass", "Needs Review", "Fail"],
                    index=["Pass", "Needs Review", "Fail"].index(eff_status) if eff_status in ["Pass", "Needs Review", "Fail"] else 1,
                    horizontal=True,
                    key=f"override_{bidder_name}_{i}"
                )
                if st.button("Apply Override", key=f"apply_{bidder_name}_{i}"):
                    st.session_state.evaluations[bidder_name]["results"][i]["override_status"] = override_val
                    # Recompute overall
                    all_results = st.session_state.evaluations[bidder_name]["results"]
                    effective_statuses = [
                        r2.get("override_status") or r2.get("status", "Needs Review")
                        for r2 in all_results
                    ]
                    if "Fail" in effective_statuses:
                        new_ov = "Not Eligible"
                    elif "Needs Review" in effective_statuses:
                        new_ov = "Needs Review"
                    else:
                        new_ov = "Eligible"
                    # Only auto-update if no manual override
                    if not st.session_state.evaluations[bidder_name].get("override_overall_status"):
                        st.session_state.evaluations[bidder_name]["overall_status"] = new_ov
                    st.success(f"Status for '{cname}' set to: {override_val}")
                    st.rerun()

        st.markdown('<hr style="border:0;border-top:1px solid #e8edf8;margin:0.5rem 0">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────
def main():
    render_sidebar()

    stage = st.session_state.stage

    if stage in ["setup", "tender"]:
        page_tender()
    elif stage == "bidders":
        page_bidders()
    elif stage == "evaluation":
        page_evaluation()
    elif stage == "results":
        page_results()
    else:
        page_tender()


if __name__ == "__main__":
    main()
