import os
import io
from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas

from app.models.case import Case
from app.models.transaction import Transaction
from app.models.detection_result import DetectionResult
from app.models.investigator_note import InvestigatorNote
from app.models.verification import Verification
from app.models.supervisor_approval import SupervisorApproval
from app.intelligence.fir_readiness import calculate_fir_readiness
from app.ai.groq_client import call_groq as query_groq

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

def add_watermark(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 60)
    canvas.setFillGray(0.5, 0.2)
    canvas.translate(300, 400)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "CONFIDENTIAL")
    canvas.restoreState()

@reports_bp.route('/generate/<case_id>', methods=['GET'])
@jwt_required()
def generate_pdf_report(case_id):
    case = Case.query.get(case_id)
    if not case:
        return jsonify({"error": "Case not found"}), 404

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#2563EB')
    )
    normal_style = styles['Normal']

    story = []

    # 1. Cover Page
    story.append(Spacer(1, 150))
    story.append(Paragraph("FINTELLIGENCE", title_style))
    story.append(Paragraph("Automated Forensic Investigation Report", title_style))
    story.append(Spacer(1, 50))
    story.append(Paragraph(f"<b>Case ID:</b> {case_id}", normal_style))
    story.append(Paragraph(f"<b>Date:</b> {case.created_at.strftime('%Y-%m-%d') if case.created_at else 'N/A'}", normal_style))
    story.append(Paragraph(f"<b>Status:</b> {case.status.upper()}", normal_style))
    story.append(PageBreak())

    # 2. Executive Summary (Mocked via Groq)
    story.append(Paragraph("Executive Summary", heading_style))
    try:
        summary_text = query_groq(f"Provide a 2-paragraph executive summary for case {case_id} involving money laundering.")
    except Exception:
        summary_text = "Executive summary generation failed or is using mock fallback."
    story.append(Paragraph(summary_text, normal_style))
    
    # 3. Risk Assessment
    story.append(Paragraph("Risk Assessment", heading_style))
    story.append(Paragraph(f"<b>Overall Risk Score:</b> {case.suspicion_score or 'N/A'}", normal_style))
    story.append(Paragraph(f"<b>Risk Level:</b> {case.risk_level or 'N/A'}", normal_style))
    
    # 4. Detector Results Summary
    story.append(Paragraph("Triggered Detectors", heading_style))
    detectors = DetectionResult.query.filter_by(case_id=case_id, triggered=True).all()
    if detectors:
        data = [["Detector", "Score", "Severity"]]
        for d in detectors:
            data.append([d.detector_name, str(d.score), d.severity])
        t = Table(data, colWidths=[200, 100, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No detectors triggered.", normal_style))

    # 5. FIR Readiness
    story.append(Paragraph("FIR Readiness Assessment", heading_style))
    fir_data = calculate_fir_readiness(case_id)
    story.append(Paragraph(f"<b>Readiness Score:</b> {fir_data.get('fir_readiness_score', 0)}", normal_style))
    story.append(Paragraph(f"<b>Ready for FIR:</b> {'Yes' if fir_data.get('ready') else 'No'}", normal_style))
    
    if fir_data.get('blocking_factors'):
        story.append(Paragraph("<b>Blocking Factors:</b>", normal_style))
        for factor in fir_data['blocking_factors']:
            story.append(Paragraph(f"- {factor}", normal_style))

    # 6. Verification Status
    story.append(Paragraph("Verification Status", heading_style))
    v = Verification.query.filter_by(case_id=case_id).first()
    if v:
        story.append(Paragraph(f"Customer Contacted: {'Yes' if v.customer_contacted else 'No'}", normal_style))
        story.append(Paragraph(f"Documents Received: {'Yes' if v.documents_received else 'No'}", normal_style))
        story.append(Paragraph(f"Source Verified: {'Yes' if v.source_verified else 'No'}", normal_style))
        story.append(Paragraph(f"Completion: {v.completion_percentage}%", normal_style))
    else:
        story.append(Paragraph("No verification record found.", normal_style))

    # Build PDF
    doc.build(story, onFirstPage=add_watermark, onLaterPages=add_watermark)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"FINTELLIGENCE_Report_{case_id}.pdf",
        mimetype='application/pdf'
    )
