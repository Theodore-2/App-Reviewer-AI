"""
App Reviewer AI - PDF Generator

Generates PDF reports from insight results.
"""

from io import BytesIO
from datetime import datetime
import logging

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.api.schemas import InsightResult

logger = logging.getLogger(__name__)


# Brand colors
PRIMARY_COLOR = HexColor("#2563EB")
SECONDARY_COLOR = HexColor("#64748B")
SUCCESS_COLOR = HexColor("#22C55E")
WARNING_COLOR = HexColor("#F59E0B")
DANGER_COLOR = HexColor("#EF4444")


def generate_pdf_report(result: InsightResult) -> bytes:
    """
    Generate a PDF report from analysis results.
    
    Args:
        result: InsightResult object
        
    Returns:
        PDF file as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=PRIMARY_COLOR,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=PRIMARY_COLOR,
        spaceBefore=20,
        spaceAfter=10
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=SECONDARY_COLOR,
        spaceBefore=10,
        spaceAfter=5
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        leading=14
    )
    
    # Build content
    story = []
    
    # Title
    story.append(Paragraph("App Review Analysis Report", title_style))
    story.append(Paragraph(
        f"Generated: {result.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        ParagraphStyle('Date', parent=body_style, alignment=TA_CENTER, textColor=SECONDARY_COLOR)
    ))
    story.append(Spacer(1, 0.25*inch))
    
    # App Info
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY_COLOR))
    story.append(Spacer(1, 0.1*inch))
    
    info_data = [
        ["App ID:", result.app_id],
        ["Platform:", result.platform.value.upper()],
        ["Reviews Analyzed:", str(result.reviews_analyzed)],
        ["Analysis Version:", result.analysis_version]
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), SECONDARY_COLOR),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.25*inch))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    story.append(Paragraph(result.summary, body_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Sentiment Breakdown
    story.append(Paragraph("Sentiment Analysis", heading_style))
    
    sentiment_data = [
        ["Sentiment", "Percentage"],
        ["Positive", f"{result.sentiment_breakdown.positive}%"],
        ["Neutral", f"{result.sentiment_breakdown.neutral}%"],
        ["Negative", f"{result.sentiment_breakdown.negative}%"]
    ]
    
    sentiment_table = Table(sentiment_data, colWidths=[2*inch, 2*inch])
    sentiment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, SECONDARY_COLOR),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sentiment_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Top Issues
    if result.top_issues:
        story.append(Paragraph("Top Issues", heading_style))
        
        issues_data = [["Issue", "Frequency", "Severity"]]
        for issue in result.top_issues[:10]:
            issues_data.append([
                issue.issue[:50] + "..." if len(issue.issue) > 50 else issue.issue,
                str(issue.frequency),
                issue.severity.value.upper()
            ])
        
        issues_table = Table(issues_data, colWidths=[3.5*inch, 1*inch, 1*inch])
        issues_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#FFFFFF")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, SECONDARY_COLOR),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(issues_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Feature Requests
    if result.feature_requests:
        story.append(Paragraph("Feature Requests", heading_style))
        
        features_data = [["Feature", "Request Count"]]
        for feature in result.feature_requests[:10]:
            features_data.append([
                feature.feature[:60] + "..." if len(feature.feature) > 60 else feature.feature,
                str(feature.count)
            ])
        
        features_table = Table(features_data, colWidths=[4.5*inch, 1*inch])
        features_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#FFFFFF")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, SECONDARY_COLOR),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(features_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Monetization Risks
    if result.monetization_risks:
        story.append(Paragraph("Monetization Risks", heading_style))
        
        risks_data = [["Risk", "Confidence"]]
        for risk in result.monetization_risks:
            risks_data.append([
                risk.risk[:60] + "..." if len(risk.risk) > 60 else risk.risk,
                risk.confidence.value.upper()
            ])
        
        risks_table = Table(risks_data, colWidths=[4.5*inch, 1*inch])
        risks_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), WARNING_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#FFFFFF")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, SECONDARY_COLOR),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(risks_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Recommended Actions
    if result.recommended_actions:
        story.append(PageBreak())
        story.append(Paragraph("Recommended Actions", heading_style))
        
        for i, action in enumerate(result.recommended_actions[:10], 1):
            priority_color = {
                "high": DANGER_COLOR,
                "medium": WARNING_COLOR,
                "low": SUCCESS_COLOR
            }.get(action.priority.value, SECONDARY_COLOR)
            
            story.append(Paragraph(
                f"<b>{i}. [{action.priority.value.upper()}]</b> {action.action}",
                body_style
            ))
            if action.expected_impact:
                story.append(Paragraph(
                    f"<i>Expected Impact: {action.expected_impact}</i>",
                    ParagraphStyle('Impact', parent=body_style, textColor=SECONDARY_COLOR, leftIndent=20)
                ))
            story.append(Spacer(1, 0.1*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=SECONDARY_COLOR))
    story.append(Paragraph(
        "Generated by App Reviewer AI",
        ParagraphStyle('Footer', parent=body_style, alignment=TA_CENTER, textColor=SECONDARY_COLOR)
    ))
    
    # Build PDF
    doc.build(story)
    
    return buffer.getvalue()
