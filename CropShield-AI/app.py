from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from app_mode import local_services_enabled
from ai_engine import OllamaError, explain_crop_problem, list_models
from crop_rules import assess_field_risk, create_action_plan
from storage import get_sample_reports, load_reports, save_report

LOCAL_MODE = local_services_enabled()

st.set_page_config(
    page_title="CropShield AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --green: #174d35; --leaf: #b7e4a1; }
    .stApp { background: linear-gradient(145deg, #f4f8f2, #edf4eb); }
    [data-testid="stSidebar"] { background: #123b2b; }
    [data-testid="stSidebar"] * { color: #f4f8f2; }
    .hero {
        padding: 1.7rem 2rem; border-radius: 1rem; color: #f8fff5;
        background: linear-gradient(110deg, #123b2b, #28734d);
        margin-bottom: 1rem;
    }
    .hero h1 { color: #f8fff5; margin-bottom: .25rem; }
    .hero p { color: #e0f0dc; margin: 0; }
    .notice {
        border-left: 4px solid #72a95b; background: #e6f1e1;
        padding: .8rem 1rem; border-radius: .35rem; color: #193d2b;
    }
    div[data-testid="stMetric"] {
        background: white; padding: 1rem; border-radius: .8rem;
        border: 1px solid #dce8d8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _format_report_rows(reports: list[dict]) -> pd.DataFrame:
    rows = []
    for report in reports:
        rows.append(
            {
                "Date": report.get("created_at", "")[:19].replace("T", " "),
                "Crop": report.get("crop", ""),
                "Growth stage": report.get("growth_stage", ""),
                "Risk": report.get("risk_level", ""),
                "Score": report.get("risk_score", 0),
                "Affected area": report.get("affected_area", ""),
                "Synthetic sample": "Yes" if report.get("synthetic") else "No",
            }
        )
    return pd.DataFrame(rows)


def _show_dashboard() -> None:
    st.subheader("Report dashboard")
    if not LOCAL_MODE:
        reports = st.session_state.setdefault("reports", [])
        st.caption(
            "Reports stay in this Streamlit session and are not written to a shared file."
        )
    else:
        try:
            reports = load_reports()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            st.error(f"Could not read saved reports: {exc}")
            reports = []

    show_samples = st.checkbox(
        "Include clearly labelled fictional sample reports", value=False
    )
    shown_reports = reports + (get_sample_reports() if show_samples else [])

    total = len(shown_reports)
    high_risk = sum(
        report.get("risk_level") == "High" for report in shown_reports
    )
    st.caption(f"{len(reports)} saved report(s); samples are demonstration data only.")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Reports shown", total)
    metric_cols[1].metric("High-risk reports", high_risk)
    metric_cols[2].metric(
        "Unique crops", len({r.get("crop", "").casefold() for r in shown_reports})
    )

    if not shown_reports:
        st.info(
            "No reports to display yet. Submit an assessment on the Crop assistant "
            "page, or enable the fictional sample reports above."
        )
        return

    table = _format_report_rows(shown_reports)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        "Download displayed reports as CSV",
        data=table.to_csv(index=False).encode("utf-8-sig"),
        file_name="cropshield_reports.csv",
        mime="text/csv",
    )

    with st.expander("View report details"):
        selected = st.selectbox(
            "Choose a report",
            range(len(shown_reports)),
            format_func=lambda index: (
                f"{shown_reports[index].get('crop', 'Unknown')} · "
                f"{shown_reports[index].get('created_at', '')[:10]} · "
                f"{'Fictional sample' if shown_reports[index].get('synthetic') else 'Saved'}"
            ),
        )
        st.json(shown_reports[selected])


def _show_assistant() -> None:
    st.subheader("Crop problem assistant")
    if LOCAL_MODE:
        st.write(
            "Record what you observe. The field-risk score is calculated locally "
            "from transparent rules; Ollama is used only to help explain possible causes."
        )
    else:
        st.write(
            "Record what you observe. Transparent rules calculate the field-risk "
            "score. AI is off in privacy-safe mode."
        )
    with st.form("crop_assessment"):
        left, right = st.columns(2)
        with left:
            crop = st.text_input("Crop name", placeholder="e.g., tomato")
            growth_stage = st.text_input(
                "Growth stage", placeholder="e.g., flowering"
            )
            affected_area = st.text_input(
                "Affected area", placeholder="e.g., north side of one field"
            )
            symptoms = st.text_area(
                "Symptoms",
                placeholder="Describe what you see, when it began, and how it is changing.",
                height=120,
            )
        with right:
            st.markdown("**Field risk checklist**")
            wilting = st.checkbox("Plants are wilting")
            yellowing = st.checkbox("Leaves are yellowing")
            standing_water = st.checkbox("Standing water is present")
            soil_moisture = st.selectbox(
                "Soil moisture", ["Unknown", "Dry", "Adequate", "Wet"]
            )
            observations = st.text_area(
                "Other observations",
                placeholder="Recent changes, affected pattern, or checks already made.",
                height=100,
            )
        if not LOCAL_MODE:
            model_name = ""
            st.info(
                "Ollama and persistent local storage are disabled by default. "
                "Run on your own trusted computer with CROPSHIELD_LOCAL_MODE=true "
                "to enable them."
            )
        else:
            model_name = st.text_input(
                "Ollama model (optional)",
                value=st.session_state.get("ollama_model", ""),
                placeholder="e.g., llama3.2",
                help="Choose or enter a model installed locally in Ollama.",
            )
        submitted = st.form_submit_button(
            "Assess and save report", type="primary", use_container_width=True
        )

    if not submitted:
        st.markdown(
            '<div class="notice">Risk flags are screening prompts, not a diagnosis. '
            "Verify important decisions with a qualified agricultural expert.</div>",
            unsafe_allow_html=True,
        )
        return

    crop = crop.strip()
    growth_stage = growth_stage.strip()
    symptoms = symptoms.strip()
    affected_area = affected_area.strip()
    observations_text = observations.strip()
    if not crop or not growth_stage or not symptoms:
        st.error("Enter a crop name, growth stage, and symptom description.")
        return
    if any(len(value) > limit for value, limit in (
        (crop, 100),
        (growth_stage, 100),
        (symptoms, 3000),
        (affected_area, 300),
        (observations_text, 3000),
    )):
        st.error("One or more fields exceed the allowed length. Please shorten them.")
        return

    field_observations = {
        "wilting": wilting,
        "yellowing": yellowing,
        "standing_water": standing_water,
        "soil_moisture": soil_moisture.casefold(),
    }
    risk = assess_field_risk(field_observations)
    action_plan = create_action_plan(risk)
    ai_explanation = ""
    follow_up_questions: list[str] = []
    ai_status = "Not requested"

    if model_name.strip():
        with st.spinner("Asking your local Ollama model…"):
            try:
                result = explain_crop_problem(
                    model=model_name.strip(),
                    crop=crop,
                    growth_stage=growth_stage,
                    symptoms=symptoms,
                    affected_area=affected_area,
                    observations=observations_text,
                    risk=risk,
                )
                ai_explanation = result["explanation"]
                follow_up_questions = result["follow_up_questions"]
                ai_status = f"Generated locally with {model_name.strip()}"
            except OllamaError as exc:
                ai_status = f"Unavailable: {exc}"
                st.warning(
                    f"Local AI explanation could not be generated. Your rule-based "
                    f"assessment is still available. {exc}"
                )
    elif LOCAL_MODE:
        st.info(
            "No Ollama model selected. The rule-based risk review and action plan "
            "are available; add an installed model name to request an explanation."
        )
    else:
        st.info(
            "AI explanations are off in privacy-safe mode. The rule-based risk "
            "review and action plan are still available."
        )

    report = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "crop": crop,
        "growth_stage": growth_stage,
        "symptoms": symptoms,
        "affected_area": affected_area,
        "observations": {
            **field_observations,
            "other_observations": observations_text,
        },
        "risk_score": risk["score"],
        "risk_level": risk["level"],
        "risk_flags": risk["flags"],
        "action_plan": action_plan,
        "ai_explanation": ai_explanation,
        "follow_up_questions": follow_up_questions,
        "ai_status": ai_status,
        "synthetic": False,
    }
    if not LOCAL_MODE:
        st.session_state.setdefault("reports", []).append(report)
    else:
        try:
            save_report(report)
        except (OSError, ValueError) as exc:
            st.error(f"Assessment completed, but the report could not be saved: {exc}")
            return

    st.session_state["latest_report"] = report
    st.success(
        "Assessment saved for this browser session."
        if LOCAL_MODE
        else "Assessment saved for this browser session."
    )

    st.markdown("### Field risk checklist")
    st.metric("Rule-based risk level", risk["level"], f"Score {risk['score']} / 10")
    if risk["flags"]:
        for flag in risk["flags"]:
            st.warning(
                f"**{flag['risk']}** — {flag['reason']} "
                f"(adds {flag['score']} point(s))"
            )
    else:
        st.success("No listed field-risk indicator was selected.")

    st.markdown("### Practical next steps")
    for step in action_plan:
        st.markdown(f"- {step}")

    st.markdown("### Possible causes and follow-up")
    if ai_explanation:
        st.write(ai_explanation)
        if follow_up_questions:
            st.markdown("**Questions that may help narrow the possibilities:**")
            for question in follow_up_questions:
                st.markdown(f"- {question}")
    else:
        st.info(
            "AI explanation unavailable for this report. Use the observations and "
            "risk flags as a starting point, not a diagnosis."
        )

    st.caption(
        "AI-generated suggestions and rule-based flags are preliminary. Consult a "
        "qualified agricultural officer or local extension service when uncertain."
    )


with st.sidebar:
    st.title("🌱 CropShield AI")
    st.caption("Local-first crop observation assistant")
    page = st.radio("Navigate", ["Crop assistant", "Report dashboard"])
    st.divider()
    st.markdown("**Ollama model status**")
    if not LOCAL_MODE:
        st.caption(
            "Privacy-safe mode: Ollama is off and reports are session-only. "
            "No cloud AI fallback is used."
        )
    else:
        try:
            installed_models = list_models()
        except OllamaError as exc:
            installed_models = []
            st.warning(str(exc))
        if installed_models:
            chosen_model = st.selectbox("Installed models", installed_models)
            st.session_state["ollama_model"] = chosen_model
            st.caption("Model runs on this computer; no cloud fallback is used.")
        else:
            st.caption("No local model detected. You can still use field-risk rules.")

st.markdown(
    '<div class="hero"><h1>CropShield AI</h1>'
    "<p>Thoughtful crop observations, explainable field checks, and cautious next steps.</p>"
    "</div>",
    unsafe_allow_html=True,
)

if page == "Crop assistant":
    _show_assistant()
else:
    _show_dashboard()
