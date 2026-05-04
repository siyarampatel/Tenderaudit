"""
modules/pdf_exporter.py
Generates a clean PDF audit report using reportlab.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import io


# Color palette
COLOR_PASS = colors.HexColor("#1a7a4a")
COLOR_FAIL = colors.HexColor("#c0392b")
COLOR_REVIEW = colors.HexColor("#d4800a")
COLOR_HEADER = colors.HexColor("#1a2744")
COLOR_SUBHEADER = colors.HexColor("#2c3e6b")
COLOR_LIGHT = colors.HexColor("#f4f6fb")
COLOR_BORDER = colors.HexColor("#d0d8e8")
COLOR_WHITE = colors.white


def _status_color(status: str):
    s = status.lower()
    if "eligible" in s and "not" not in s:
        return COLOR_PASS
    if "not eligible" in s or "fail" in s:
        return COLOR_FAIL
    return COLOR_REVIEW


def generate_report(tender_name: str, criteria: list, bidders: list) -> bytes:
    """
    Generate a complete PDF evaluation report.
    
    Args:
        tender_name: Name/title of the tender
        criteria: List of criterion dicts
        bidders: List of bidder evaluation dicts (with 'results' key)
    
    Returns: PDF as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Title Page ──────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        'Title', parent=styles['Normal'],
        fontSize=20, textColor=COLOR_HEADER,
        spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=12, textColor=COLOR_SUBHEADER,
        spaceAfter=4, alignment=TA_CENTER
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor("#333333"),
        spaceAfter=3, leading=14
    )
    small_style = ParagraphStyle(
        'Small', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor("#555555"),
        spaceAfter=2
    )

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("TenderAudit", title_style))
    story.append(Paragraph("Government Tender Eligibility Evaluation Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_HEADER, spaceAfter=12))
    story.append(Spacer(1, 0.3*cm))

    meta_data = [
        ["Tender / Reference:", tender_name],
        ["Report Generated:", datetime.now().strftime("%d %B %Y, %I:%M %p")],
        ["Total Bidders Evaluated:", str(len(bidders))],
        ["Total Criteria:", str(len(criteria))],
    ]
    meta_table = Table(meta_data, colWidths=[5*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), COLOR_SUBHEADER),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Summary Table ────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", ParagraphStyle(
        'SectionHead', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold',
        textColor=COLOR_HEADER, spaceAfter=8
    )))

    summary_headers = [["Bidder Name", "Overall Status", "Confidence", "Passed", "Flagged", "Failed"]]
    summary_rows = []
    for b in bidders:
        results = b.get("results", [])
        passed = sum(1 for r in results if r.get("status") == "Pass" or r.get("override_status") == "Pass")
        failed = sum(1 for r in results if r.get("status") == "Fail" or r.get("override_status") == "Fail")
        flagged = len(results) - passed - failed
        overall = b.get("override_overall_status") or b.get("overall_status", "Needs Review")
        conf = b.get("avg_confidence", 0)
        summary_rows.append([
            b.get("bidder_name", "Unknown"),
            overall,
            f"{conf:.0f}%",
            str(passed),
            str(flagged),
            str(failed)
        ])

    summary_table = Table(
        summary_headers + summary_rows,
        colWidths=[4.5*cm, 3.5*cm, 2.5*cm, 2*cm, 2*cm, 2*cm]
    )
    summary_style = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_LIGHT, COLOR_WHITE]),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]
    # Color-code status cells
    for i, b in enumerate(bidders):
        overall = b.get("override_overall_status") or b.get("overall_status", "Needs Review")
        row = i + 1
        c = _status_color(overall)
        summary_style.append(('TEXTCOLOR', (1, row), (1, row), c))
        summary_style.append(('FONTNAME', (1, row), (1, row), 'Helvetica-Bold'))

    summary_table.setStyle(TableStyle(summary_style))
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Eligibility Criteria ─────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Eligibility Criteria", ParagraphStyle(
        'SectionHead', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold',
        textColor=COLOR_HEADER, spaceAfter=8
    )))

    crit_headers = [["#", "Criterion", "Type", "Required Value", "Unit"]]
    crit_rows = [[
        str(i+1),
        c.get("criterion_name", ""),
        c.get("type", ""),
        c.get("required_value", ""),
        c.get("unit", "")
    ] for i, c in enumerate(criteria)]

    crit_table = Table(crit_headers + crit_rows, colWidths=[1*cm, 5.5*cm, 3*cm, 4*cm, 3*cm])
    crit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_SUBHEADER),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_LIGHT, COLOR_WHITE]),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(crit_table)

    # ── Per-Bidder Detail ────────────────────────────────────────────────
    for b in bidders:
        story.append(PageBreak())
        bidder_name = b.get("bidder_name", "Unknown Bidder")
        overall = b.get("override_overall_status") or b.get("overall_status", "Needs Review")
        conf = b.get("avg_confidence", 0)

        story.append(Paragraph(f"Bidder: {bidder_name}", ParagraphStyle(
            'BidderHead', parent=styles['Normal'],
            fontSize=14, fontName='Helvetica-Bold',
            textColor=COLOR_HEADER, spaceAfter=4
        )))

        # Status badge row
        badge_color = _status_color(overall)
        badge_data = [[
            Paragraph(f"Overall Status: <b>{overall}</b>", ParagraphStyle(
                'Badge', parent=styles['Normal'],
                fontSize=10, textColor=badge_color, fontName='Helvetica-Bold'
            )),
            Paragraph(f"Avg. Confidence: <b>{conf:.0f}%</b>", ParagraphStyle(
                'Badge2', parent=styles['Normal'],
                fontSize=10, textColor=COLOR_SUBHEADER
            )),
        ]]
        badge_table = Table(badge_data, colWidths=[9*cm, 7*cm])
        badge_table.setStyle(TableStyle([
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(badge_table)

        if b.get("override_overall_status"):
            story.append(Paragraph(
                f"⚑ Officer Override Applied: Status changed to {b['override_overall_status']}",
                ParagraphStyle('Override', parent=styles['Normal'],
                    fontSize=8, textColor=colors.HexColor("#8b6914"),
                    spaceAfter=6, fontName='Helvetica-Oblique')
            ))

        story.append(Spacer(1, 0.3*cm))

        # Detail table
        det_headers = [["Criterion", "Required", "Extracted Value", "Source", "Conf.", "Status", "Override"]]
        det_rows = []
        results = b.get("results", [])
        for r in results:
            cname = r.get("criterion_name", "")
            # Find required value
            req_val = ""
            for c in criteria:
                if c.get("criterion_name", "").lower() == cname.lower():
                    req_val = f"{c.get('required_value','')} {c.get('unit','')}".strip()
                    break

            eff_status = r.get("override_status") or r.get("status", "Needs Review")
            src_page = r.get("source_page", 0)
            source_str = f"Pg {src_page}" if src_page and src_page > 0 else "N/A"
            override_str = r.get("override_status", "") or "-"

            det_rows.append([
                cname,
                req_val,
                r.get("extracted_value", "Not Found"),
                source_str,
                f"{r.get('confidence', 0)}%",
                eff_status,
                override_str
            ])

        det_table = Table(
            det_headers + det_rows,
            colWidths=[3.5*cm, 2.5*cm, 3*cm, 1.5*cm, 1.2*cm, 2*cm, 2.8*cm]
        )
        det_style = [
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_SUBHEADER),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_LIGHT, COLOR_WHITE]),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]
        # Color status column
        for i, r in enumerate(results):
            eff_status = r.get("override_status") or r.get("status", "Needs Review")
            row = i + 1
            c = _status_color(eff_status)
            det_style.append(('TEXTCOLOR', (5, row), (5, row), c))
            det_style.append(('FONTNAME', (5, row), (5, row), 'Helvetica-Bold'))

        det_table.setStyle(TableStyle(det_style))
        story.append(det_table)

    # ── Footer note ──────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "This report was generated by TenderAudit. All AI evaluations are advisory. "
        "Final eligibility decisions rest with the designated procurement authority.",
        ParagraphStyle('Footer', parent=styles['Normal'],
            fontSize=7.5, textColor=colors.HexColor("#888888"),
            alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()
