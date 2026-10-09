"""
Script to generate FIN_MultiPage_Income_Certificate_QA.pdf
4-page, A4, text-searchable, synthetic Indian government-style Income Certificate
specifically formatted for testing FIN PDF extraction and dynamic page citation.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Arial for clean rendering and Rupee (₹) symbol support
FONT_PATH = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/arialbd.ttf"
FONT_ITALIC_PATH = "C:/Windows/Fonts/ariali.ttf"

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("Arial", FONT_PATH))
    font_normal = "Arial"
else:
    font_normal = "Helvetica"

if os.path.exists(FONT_BOLD_PATH):
    pdfmetrics.registerFont(TTFont("Arial-Bold", FONT_BOLD_PATH))
    font_bold = "Arial-Bold"
else:
    font_bold = "Helvetica-Bold"

if os.path.exists(FONT_ITALIC_PATH):
    pdfmetrics.registerFont(TTFont("Arial-Italic", FONT_ITALIC_PATH))
    font_italic = "Arial-Italic"
else:
    font_italic = "Helvetica-Oblique"


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to draw:
    1. Diagonal watermark on every page: "SYNTHETIC TEST DOCUMENT — NOT VALID FOR OFFICIAL USE"
    2. Professional official header & double border
    3. Exact footer: "FIN QA TEST DOCUMENT | Page X of 4"
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        w, h = A4

        # 1. Outer & Inner Official Double Border
        self.setStrokeColor(colors.HexColor("#1A365D"))  # Deep Navy Blue
        self.setLineWidth(1.5)
        self.rect(24, 24, w - 48, h - 48)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))  # Slate Border
        self.setLineWidth(0.75)
        self.rect(28, 28, w - 56, h - 56)

        # 2. Prominent Diagonal Watermark on every page
        self.saveState()
        self.translate(w / 2.0, h / 2.0)
        self.rotate(45)
        self.setFont(font_bold, 24)
        self.setFillColor(colors.HexColor("#E2E8F0"), alpha=0.35)
        self.drawCentredString(0, 40, "SYNTHETIC TEST DOCUMENT")
        self.setFont(font_bold, 18)
        self.drawCentredString(0, 10, "NOT VALID FOR OFFICIAL USE")
        self.setFont(font_normal, 12)
        self.drawCentredString(0, -16, "CREATED EXCLUSIVELY FOR FIN QA AUTOMATION")
        self.restoreState()

        # 3. Top Administrative Banner (inside border)
        self.setFillColor(colors.HexColor("#1E3A8A"))  # Navy
        self.rect(28, h - 68, w - 56, 40, fill=1, stroke=0)

        self.setFillColor(colors.white)
        self.setFont(font_bold, 11)
        self.drawCentredString(w / 2.0, h - 44, "GOVERNMENT OF GUJARAT (FICTIONAL TEST AUTHORITY)")
        self.setFont(font_normal, 8.5)
        self.drawCentredString(w / 2.0, h - 56, "DISTRICT REVENUE OFFICE, AHMEDABAD • TALUKA: DASKROI • SUB-DIVISION: URBAN")
        self.setFont(font_italic, 7)
        self.drawCentredString(w / 2.0, h - 65, "[SYNTHETIC TEST INSTRUMENT • PREPARED STRICTLY FOR SYSTEM INTEGRATION TESTING]")

        # 4. Consistent Reference Strip under top banner
        self.setFillColor(colors.HexColor("#F8FAFC"))
        self.rect(28, h - 86, w - 56, 18, fill=1, stroke=0)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(28, h - 86, w - 28, h - 86)

        self.setFillColor(colors.HexColor("#334155"))
        self.setFont(font_bold, 7.5)
        self.drawString(36, h - 80, "CERTIFICATE NO: TEST/GJ/INC/2026/TEST-84729")
        self.drawCentredString(w / 2.0, h - 80, "APPLICATION REF: FIN-QA-2026-00481")
        self.drawRightString(w - 36, h - 80, "FINANCIAL YEAR: 2025–2026 | ISSUE: 18-SEP-2026")

        # 5. Bottom Footer (Mandatory Requirement)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(28, 48, w - 28, 48)

        self.setFillColor(colors.HexColor("#475569"))
        self.setFont(font_bold, 8.5)
        # Exact requested footer text: "FIN QA TEST DOCUMENT | Page X of 4"
        footer_text = f"FIN QA TEST DOCUMENT | Page {self._pageNumber} of {page_count}"
        self.drawString(36, 36, footer_text)

        self.setFont(font_normal, 7)
        self.drawRightString(w - 36, 36, "SYNTHETIC TEST DOCUMENT — NOT VALID FOR OFFICIAL USE")
        self.drawCentredString(w / 2.0, 30, "Automated QA Verification Artifact • Fictional Administrative Record • No Statutory Privilege")

        self.restoreState()


def create_income_certificate_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=94,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styling
    title_style = ParagraphStyle(
        "CertTitle",
        fontName=font_bold,
        fontSize=13,
        leading=16,
        alignment=1,  # Center
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3,
    )

    subtitle_style = ParagraphStyle(
        "CertSubtitle",
        fontName=font_normal,
        fontSize=8.5,
        leading=11,
        alignment=1,  # Center
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        fontName=font_bold,
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=6,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "CertBody",
        fontName=font_normal,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1E293B"),
    )

    body_bold = ParagraphStyle(
        "CertBodyBold",
        fontName=font_bold,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
    )

    notice_style = ParagraphStyle(
        "NoticeStyle",
        fontName=font_italic,
        fontSize=7.5,
        leading=10,
        alignment=1,
        textColor=colors.HexColor("#64748B"),
    )

    highlight_statement_style = ParagraphStyle(
        "HighlightStatement",
        fontName=font_bold,
        fontSize=9,
        leading=13,
        alignment=1,  # Centered
        textColor=colors.HexColor("#0F172A"),
    )

    disclaimer_style = ParagraphStyle(
        "DisclaimerStyle",
        fontName=font_normal,
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#7F1D1D"),
    )

    story = []

    # =========================================================================
    # PAGE 1 — Applicant Identification
    # CRITICAL: DO NOT include annual family income amount anywhere on Page 1!
    # =========================================================================
    story.append(Paragraph("ANNUAL FAMILY INCOME CERTIFICATE", title_style))
    story.append(Paragraph("FORM 16-B (FICTIONAL) • STATUTORY CITIZEN IDENTIFICATION RECORD", subtitle_style))

    # Notice callout
    notice_text = (
        "<b>ADMINISTRATIVE NOTICE:</b> This page contains verified applicant identification, familial records, "
        "and administrative jurisdiction details. In accordance with statutory procedure, the comprehensive "
        "<b>Family Income Assessment is recorded separately on Page 2</b> of this document."
    )
    notice_table = Table(
        [[Paragraph(notice_text, notice_style)]],
        colWidths=[523],
    )
    notice_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(notice_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. APPLICANT IDENTIFICATION DETAILS", section_heading))
    p1_applicant_data = [
        [
            Paragraph("<b>Applicant Full Name:</b>", body_style),
            Paragraph("Aarav Patel", body_bold),
            Paragraph("<b>Gender:</b>", body_style),
            Paragraph("Male", body_style),
        ],
        [
            Paragraph("<b>Date of Birth:</b>", body_style),
            Paragraph("12 August 2004", body_style),
            Paragraph("<b>Completed Age:</b>", body_style),
            Paragraph("22 Years", body_style),
        ],
        [
            Paragraph("<b>Father's Full Name:</b>", body_style),
            Paragraph("Mahesh Patel", body_style),
            Paragraph("<b>Mother's Full Name:</b>", body_style),
            Paragraph("Nisha Patel", body_style),
        ],
        [
            Paragraph("<b>Social Category:</b>", body_style),
            Paragraph("<b>SC</b> (Scheduled Caste)", body_style),
            Paragraph("<b>Nationality:</b>", body_style),
            Paragraph("Indian", body_style),
        ],
        [
            Paragraph("<b>Aadhaar Reference Token:</b>", body_style),
            Paragraph("XXXX-XXXX-8429 (Verified Biometric)", body_style),
            Paragraph("<b>Marital Status:</b>", body_style),
            Paragraph("Unmarried", body_style),
        ],
    ]
    t1_app = Table(p1_applicant_data, colWidths=[140, 150, 110, 123])
    t1_app.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F8FAFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t1_app)
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. DOMICILE & RESIDENTIAL JURISDICTION", section_heading))
    p1_residence_data = [
        [
            Paragraph("<b>Residential Address:</b>", body_style),
            Paragraph("24, Shantivan Residency, Ahmedabad, Gujarat", body_bold),
        ],
        [
            Paragraph("<b>Village / City:</b>", body_style),
            Paragraph("Ahmedabad (Ward 14)", body_style),
        ],
        [
            Paragraph("<b>Taluka / Tahsil:</b>", body_style),
            Paragraph("Daskroi", body_style),
        ],
        [
            Paragraph("<b>District:</b>", body_style),
            Paragraph("Ahmedabad", body_style),
        ],
        [
            Paragraph("<b>State / Union Territory:</b>", body_style),
            Paragraph("Gujarat", body_style),
        ],
        [
            Paragraph("<b>Continuous Domicile Duration:</b>", body_style),
            Paragraph("18 Years (Permanent Domiciliary Record Verified)", body_style),
        ],
    ]
    t1_res = Table(p1_residence_data, colWidths=[150, 373])
    t1_res.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t1_res)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. CERTIFICATE ISSUANCE & STATUTORY METADATA", section_heading))
    p1_meta_data = [
        [
            Paragraph("<b>Certificate Number:</b>", body_style),
            Paragraph("TEST/GJ/INC/2026/TEST-84729", body_bold),
            Paragraph("<b>Document Type:</b>", body_style),
            Paragraph("Annual Family Income Certificate", body_style),
        ],
        [
            Paragraph("<b>Application Reference:</b>", body_style),
            Paragraph("FIN-QA-2026-00481", body_bold),
            Paragraph("<b>Issue Date:</b>", body_style),
            Paragraph("18 September 2026", body_style),
        ],
        [
            Paragraph("<b>Financial Year Covered:</b>", body_style),
            Paragraph("2025–2026", body_bold),
            Paragraph("<b>Issuing Authority:</b>", body_style),
            Paragraph("Fictional District Revenue Office, Ahmedabad", body_style),
        ],
        [
            Paragraph("<b>Inward Application Date:</b>", body_style),
            Paragraph("04 September 2026", body_style),
            Paragraph("<b>Verification Level:</b>", body_style),
            Paragraph("Talati & Revenue Inspector Endorsed", body_style),
        ],
    ]
    t1_meta = Table(p1_meta_data, colWidths=[140, 150, 110, 123])
    t1_meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F8FAFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t1_meta)
    story.append(Spacer(1, 10))

    # Officer note
    officer_note = (
        "<b>CERTIFYING OFFICER'S INITIAL NOTE:</b> The identity and domicile credentials of applicant "
        "<b>Aarav Patel</b> have been verified against municipal records of Ahmedabad district. "
        "Pursuant to Gujarat State Revenue Manual Guidelines, the financial inquiries into family livelihood "
        "and statutory assessment are documented on <b>Page 2</b> of this four-page record."
    )
    story.append(Paragraph(officer_note, body_style))

    # =========================================================================
    # PAGE 2 — Family Income Assessment
    # CRITICAL: This page MUST contain the authoritative income figure: ₹1,80,000
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("SCHEDULE A: STATUTORY ANNUAL FAMILY INCOME ASSESSMENT", title_style))
    story.append(Paragraph("DETAILED EARNINGS EVALUATION • FINANCIAL YEAR 2025–2026", subtitle_style))

    # Mandatory statement that this page contains the income assessment
    p2_intro = (
        "<b>STATEMENT OF JURISDICTION & SCOPE:</b> This page contains the authoritative annual family income "
        "assessment for the applicant's household, established through field inspection, revenue inquiry, and "
        "competent revenue officer evaluation for <b>Certificate Number TEST/GJ/INC/2026/TEST-84729</b>."
    )
    story.append(Paragraph(p2_intro, body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. ANNUAL HOUSEHOLD INCOME COMPUTATION", section_heading))

    # EXACT MANDATED TABLE
    table_headers = [
        Paragraph("<b>Income Component</b>", body_bold),
        Paragraph("<b>Contributing Household Earner</b>", body_bold),
        Paragraph("<b>Nature of Livelihood / Occupation</b>", body_bold),
        Paragraph("<b>Annual Amount</b>", body_bold),
    ]
    table_rows = [
        table_headers,
        [
            Paragraph("Father's Employment Income", body_style),
            Paragraph("Mahesh Patel (Father)", body_style),
            Paragraph("Clerical and administrative assistance in local shop", body_style),
            Paragraph("₹1,20,000", body_bold),
        ],
        [
            Paragraph("Mother's Self-Employment Income", body_style),
            Paragraph("Nisha Patel (Mother)", body_style),
            Paragraph("Tailoring, dressmaking and handicraft work", body_style),
            Paragraph("₹60,000", body_bold),
        ],
        [
            Paragraph("Other Family Income", body_style),
            Paragraph("Household Collective", body_style),
            Paragraph("Agricultural land, rental, interest, or commercial gains", body_style),
            Paragraph("₹0", body_bold),
        ],
        [
            Paragraph("<b>Total Annual Family Income</b>", body_bold),
            Paragraph("<b>All Household Earners</b>", body_bold),
            Paragraph("<b>Consolidated Family Annual Earnings</b>", body_bold),
            Paragraph("<b>₹1,80,000</b>", body_bold),
        ],
    ]

    income_table = Table(table_rows, colWidths=[185, 115, 133, 90])
    income_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FEF08A")),  # Soft highlight on total row
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(income_table)
    story.append(Spacer(1, 10))

    # EXACT MANDATED STATEMENT IN BOX
    exact_income_statement = (
        "Total annual family income of the applicant's household for the financial year 2025–2026 is "
        "₹1,80,000 (Rupees One Lakh Eighty Thousand Only)."
    )
    cert_box = Table(
        [[
            Paragraph(f"<b>OFFICIAL STATUTORY DETERMINATION:</b><br/>{exact_income_statement}", highlight_statement_style)
        ]],
        colWidths=[523],
    )
    cert_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF9C3")),  # Warm yellow highlight
        ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#CA8A04")),     # Gold-amber border
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(cert_box)
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. ASSESSMENT PARAMETERS & CALCULATION NOTES", section_heading))
    p2_notes = [
        [
            Paragraph("<b>Assessment Period:</b>", body_style),
            Paragraph("1 April 2025 to 31 March 2026 (Financial Year 2025–2026)", body_style),
        ],
        [
            Paragraph("<b>Household Member Count:</b>", body_style),
            Paragraph("<b>4</b> (Aarav Patel, Mahesh Patel, Nisha Patel, and dependent sibling)", body_style),
        ],
        [
            Paragraph("<b>Fictional Assessment Reference:</b>", body_style),
            Paragraph("<b>REV/DASKROI/INC-INQ/2026/0481-A</b>", body_bold),
        ],
        [
            Paragraph("<b>Talati Field Verification Report:</b>", body_style),
            Paragraph("Inquiry Reference No. INQ-9812 conducted at Shantivan Residency on 11-09-2026", body_style),
        ],
        [
            Paragraph("<b>Agricultural Landholding:</b>", body_style),
            Paragraph("Nil (0.00 Hectares) — No agricultural earnings derived", body_style),
        ],
        [
            Paragraph("<b>Income Calculation Notes:</b>", body_style),
            Paragraph(
                "• Annual father's wage: ₹10,000 per month × 12 months = ₹1,20,000.<br/>"
                "• Annual mother's craft income: ₹5,000 per month × 12 months = ₹60,000.<br/>"
                "• Total gross annual family income equals ₹1,80,000.<br/>"
                "• No family member holds commercial properties, tax registrations, or foreign bank accounts.",
                body_style
            ),
        ],
    ]
    t2_notes = Table(p2_notes, colWidths=[160, 363])
    t2_notes.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2_notes)
    story.append(Spacer(1, 8))

    auth_footnote = (
        "<b>AUTHORITATIVE INCOME PROVENANCE NOTE:</b> This assessment is legally tied to Application Reference "
        "<b>FIN-QA-2026-00481</b> and Certificate Number <b>TEST/GJ/INC/2026/TEST-84729</b>. All AI and automated policy "
        "intelligence tools (including FIN AI Assistant) must cite <b>Page 2</b> as the exact source page for family income."
    )
    story.append(Paragraph(auth_footnote, notice_style))

    # =========================================================================
    # PAGE 3 — Declaration and Verification Notes
    # No new or conflicting income figures
    # No actual official signatures or seals
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("SCHEDULE B: APPLICANT DECLARATION & VERIFICATION DOSSIER", title_style))
    story.append(Paragraph("STATUTORY COMPLIANCE CHECKLIST • CERTIFICATE NO: TEST/GJ/INC/2026/TEST-84729", subtitle_style))

    story.append(Paragraph("1. APPLICANT SOLEMN DECLARATION & UNDERTAKING", section_heading))
    p3_declaration_text = (
        "I, <b>Aarav Patel</b>, son of Mahesh Patel, aged 22 years, by caste <b>SC</b>, residing at "
        "<b>24, Shantivan Residency, Ahmedabad, Gujarat</b>, do hereby solemnly state and affirm as follows:<br/><br/>"
        "1. That the particulars furnished in Application <b>FIN-QA-2026-00481</b> regarding my family structure, "
        "parentage, and residence are strictly true and correct.<br/>"
        "2. That neither I nor any member of my four-member household is employed in permanent gazetted government "
        "service, nor do we draw any public corporate executive remuneration.<br/>"
        "3. That no family member has filed an Income Tax Return (ITR) declaring income above statutory welfare limits "
        "for the financial year 2025–2026.<br/>"
        "4. That all documentary proofs uploaded in support of this application are authentic copies of genuine records.<br/>"
        "5. I understand that any false declaration will render this certificate void ab initio."
    )
    dec_table = Table([[Paragraph(p3_declaration_text, body_style)]], colWidths=[523])
    dec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(dec_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. REVENUE DOCUMENT REVIEW CHECKLIST", section_heading))
    doc_checklist = [
        [
            Paragraph("<b>Document / Credential Inspected</b>", body_bold),
            Paragraph("<b>Issuing Authority / Reference</b>", body_bold),
            Paragraph("<b>Verification Result</b>", body_bold),
        ],
        [
            Paragraph("Identity Proof (Aadhaar Card of Applicant)", body_style),
            Paragraph("UIDAI Reference ending with -8429", body_style),
            Paragraph("✅ VERIFIED (Identity Match Confirmed)", body_style),
        ],
        [
            Paragraph("Proof of Residence (Electricity Bill & Domicile)", body_style),
            Paragraph("UGVCL Bill No. AHM-884210", body_style),
            Paragraph("✅ VERIFIED (Residence at 24, Shantivan)", body_style),
        ],
        [
            Paragraph("Social Category Certificate (SC)", body_style),
            Paragraph("Social Welfare Dept Ref: GUJ/SC/2021/491", body_style),
            Paragraph("✅ VERIFIED (Category: SC)", body_style),
        ],
        [
            Paragraph("Ration Card / Family Composition Dossier", body_style),
            Paragraph("Civil Supplies Office, Ahmedabad Urban", body_style),
            Paragraph("✅ VERIFIED (Household Members: 4)", body_style),
        ],
        [
            Paragraph("Local Field Revenue Inquiry Dossier", body_style),
            Paragraph("Talati Office, Daskroi Sub-Division", body_style),
            Paragraph("✅ COMPLETED (Findings Endorsed)", body_style),
        ],
    ]
    t3_check = Table(doc_checklist, colWidths=[185, 178, 160])
    t3_check.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t3_check)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. FICTIONAL ADMINISTRATIVE REMARKS", section_heading))
    admin_remarks = (
        "• <b>Field Verification Date:</b> 11 September 2026 by Revenue Circle Inspector.<br/>"
        "• <b>Physical Inspection Summary:</b> The applicant resides in a modest residential tenement. "
        "The economic circumstances observed during field inquiry are consistent with the income assessment.<br/>"
        "• <b>Conflict Check:</b> No divergent income figures or conflicting family affidavits were discovered on file.<br/>"
        "• <b>Authentication Notice:</b> [FICTIONAL ADMINISTRATIVE TEST RECORD — NO OFFICIAL SIGNATURE REQUIRED]. "
        "Generated as a synthetic test sample for evaluating automated NLP / RAG extraction engines."
    )
    story.append(Paragraph(admin_remarks, body_style))

    # =========================================================================
    # PAGE 4 — Administrative Record
    # Summary of certificate details repeated, QA metadata, legal disclaimer
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("SCHEDULE C: ADMINISTRATIVE AUDIT RECORD & QA LEDGER", title_style))
    story.append(Paragraph("DISPATCH REGISTER ARCHIVE • DOCUMENT STATUS: SYNTHETIC QA SAMPLE", subtitle_style))

    story.append(Paragraph("1. CERTIFICATE ISSUE & ATTRIBUTE SUMMARY", section_heading))
    summary_data = [
        [
            Paragraph("<b>Attribute</b>", body_bold),
            Paragraph("<b>Authoritative Value Recorded</b>", body_bold),
            Paragraph("<b>Cross-Reference Notes</b>", body_bold),
        ],
        [
            Paragraph("Applicant Full Name", body_style),
            Paragraph("<b>Aarav Patel</b>", body_bold),
            Paragraph("Consistent with Pages 1, 2, 3, 4", body_style),
        ],
        [
            Paragraph("Father's Name", body_style),
            Paragraph("Mahesh Patel", body_style),
            Paragraph("Household Primary Earner", body_style),
        ],
        [
            Paragraph("Mother's Name", body_style),
            Paragraph("Nisha Patel", body_style),
            Paragraph("Household Secondary Earner", body_style),
        ],
        [
            Paragraph("Social Category", body_style),
            Paragraph("<b>SC</b>", body_bold),
            Paragraph("Eligible for Statutory Margin & Subsidies", body_style),
        ],
        [
            Paragraph("Certificate Number", body_style),
            Paragraph("<b>TEST/GJ/INC/2026/TEST-84729</b>", body_bold),
            Paragraph("Master Revenue File Index", body_style),
        ],
        [
            Paragraph("Application Reference", body_style),
            Paragraph("<b>FIN-QA-2026-00481</b>", body_bold),
            Paragraph("Inward Tracking Identifier", body_style),
        ],
        [
            Paragraph("Financial Year", body_style),
            Paragraph("<b>2025–2026</b>", body_bold),
            Paragraph("Assessment Base (Page 2 Source)", body_style),
        ],
        [
            Paragraph("Certificate Issue Date", body_style),
            Paragraph("18 September 2026", body_style),
            Paragraph("Dispatch Docket Recorded", body_style),
        ],
        [
            Paragraph("Issuing Authority", body_style),
            Paragraph("Fictional District Revenue Office, Ahmedabad", body_style),
            Paragraph("District Administrative Complex", body_style),
        ],
        [
            Paragraph("Document Status", body_style),
            Paragraph("<b>Synthetic QA Sample</b>", body_bold),
            Paragraph("Non-Statutory Automated Test Artifact", body_style),
        ],
    ]
    t4_summary = Table(summary_data, colWidths=[140, 200, 183])
    t4_summary.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t4_summary)
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. FICTIONAL OFFICE & DISPATCH REGISTRY", section_heading))
    office_details = [
        [
            Paragraph("<b>Administrative Office:</b>", body_style),
            Paragraph("Office of the Assistant Revenue Commissioner, Ahmedabad Urban Complex, Ashram Road, Ahmedabad, Gujarat - 380009", body_style),
        ],
        [
            Paragraph("<b>Dispatch Register Folio:</b>", body_style),
            Paragraph("VOL-IV / 2026 / PAGE-184 • Entry Sequence # 942", body_style),
        ],
        [
            Paragraph("<b>Public Service Benchmark:</b>", body_style),
            Paragraph("Gujarat Citizen Service Guarantee Framework (Fictional Protocol)", body_style),
        ],
        [
            Paragraph("<b>Intended Testing Role:</b>", body_style),
            Paragraph("Verification of Dynamic Multi-Page Fact Citation in FIN Assistant (Income on Page 2)", body_style),
        ],
    ]
    t4_office = Table(office_details, colWidths=[150, 373])
    t4_office.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t4_office)
    story.append(Spacer(1, 10))

    # MANDATORY LEGAL DISCLAIMER BOX
    legal_disclaimer_text = (
        "<b>IMPORTANT STATUTORY & QA DISCLAIMER:</b><br/>"
        "This document is an entirely fictional, synthetic test instrument created exclusively for software quality assurance, "
        "automated PDF text extraction, and dynamic page-level citation verification in the FIN (Financial Policy Intelligence) application. "
        "It does <b>NOT</b> represent an official certificate issued by the Government of Gujarat, the Revenue Department, or any statutory authority. "
        "This document confers <b>NO</b> legal rights, social welfare benefits, subsidy claims, or administrative authority whatsoever. "
        "Any presentation, reproduction, or use of this document for official government procedures or fraudulent claims is strictly prohibited."
    )
    disclaimer_box = Table(
        [[Paragraph(legal_disclaimer_text, disclaimer_style)]],
        colWidths=[523],
    )
    disclaimer_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),  # Light red alert background
        ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#DC2626")),     # Red alert border
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(disclaimer_box)

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Document successfully created at: {output_path}")


if __name__ == "__main__":
    target_path = "FIN_MultiPage_Income_Certificate_QA.pdf"
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    create_income_certificate_pdf(target_path)
