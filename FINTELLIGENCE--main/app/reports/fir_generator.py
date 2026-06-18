from flask import send_file, jsonify
from flask_jwt_extended import jwt_required

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet

from app.reports.report_generator import reports_bp
from app.models.case import Case
from app.models.verification import Verification
from app.models.supervisor_approval import SupervisorApproval
from app.intelligence.fir_readiness import calculate_fir_readiness
from app.ai.groq_client import call_groq as query_groq

import os


@reports_bp.route('/fir-draft/<case_id>', methods=['POST'])
@jwt_required()
def generate_fir_draft(case_id):

    # --------------------------------------------------
    # Validate Case
    # --------------------------------------------------
    case = Case.query.get(case_id)

    if not case:
        return jsonify({
            "error": "Case not found"
        }), 404

    # --------------------------------------------------
    # Verification Status
    # --------------------------------------------------
    verification = Verification.query.filter_by(
        case_id=case_id
    ).first()

    verification_pct = (
        verification.completion_percentage
        if verification
        else 0.0
    )

    # --------------------------------------------------
    # Supervisor Approval
    # --------------------------------------------------
    approval = (
        SupervisorApproval.query
        .filter_by(case_id=case_id)
        .order_by(
            SupervisorApproval.requested_at.desc()
        )
        .first()
    )

    approval_status = (
        approval.status
        if approval
        else "none"
    )

    # --------------------------------------------------
    # FIR Readiness Check
    # --------------------------------------------------
    fir_data = calculate_fir_readiness(case_id)

    gate_open = all([
        verification_pct == 100.0,
        approval_status == "approved",
        fir_data.get("ready", False)
    ])

    if not gate_open:
        return jsonify({
            "error": "FIR gate is closed",
            "blocking_factors": fir_data.get(
                "blocking_factors",
                []
            )
        }), 403

    # --------------------------------------------------
    # Build AI Prompt
    # --------------------------------------------------
    prompt = f"""
Generate a professional Indian FIR draft.

Case ID: {case_id}

Risk Level: {case.risk_level}
Suspicion Score: {case.suspicion_score}

Include:

1. FIR Header
2. Complainant Details
3. Accused Account Details
4. Nature of Offence
5. Detailed Transaction Summary
6. Evidence Summary
7. Findings of Investigation
8. Applicable Sections
   - IPC 420
   - IPC 467
   - IPC 468
   - PMLA Section 3
9. Relief Sought
10. Conclusion

Return only the FIR document.
"""

    # --------------------------------------------------
    # Generate FIR Using Groq
    # --------------------------------------------------
    try:
        system_prompt = "You are an expert legal assistant drafting First Information Reports (FIR) for financial fraud."
        fir_text = query_groq(system_prompt, prompt)

        if not fir_text:
            raise Exception(
                "Empty response received from Groq"
            )

    except Exception as e:

        print("=" * 60)
        print("GROQ FIR GENERATION ERROR")
        print(str(e))
        print("=" * 60)

        return jsonify({
            "error": "Failed to generate FIR",
            "details": str(e)
        }), 500

    # --------------------------------------------------
    # Create PDF
    # --------------------------------------------------
    from flask import current_app
    reports_dir = os.path.join(current_app.root_path, "generated_reports")
    os.makedirs(reports_dir, exist_ok=True)

    pdf_path = os.path.join(
        reports_dir,
        f"FIR_{case_id}.pdf"
    )

    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(pdf_path)

    story = []

    story.append(
        Paragraph(
            "FIRST INFORMATION REPORT",
            styles["Title"]
        )
    )

    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            f"<b>Case ID:</b> {case_id}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Risk Level:</b> {case.risk_level}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Suspicion Score:</b> "
            f"{round(case.suspicion_score, 1)}",
            styles["Normal"]
        )
    )

    story.append(Spacer(1, 20))

    fir_paragraphs = fir_text.split("\n")

    for line in fir_paragraphs:

        if line.strip():

            story.append(
                Paragraph(
                    line,
                    styles["BodyText"]
                )
            )

            story.append(
                Spacer(1, 4)
            )

    doc.build(story)

    # --------------------------------------------------
    # Return Downloadable PDF
    # --------------------------------------------------
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"FIR_{case_id}.pdf",
        mimetype="application/pdf"
    )