"""
Controlled Test PDF Generator for FIN Document Intelligence Audit.
Generates:
  1. test_a_single_page.pdf: Single-page certificate with Aarav Patel, TEST/GJ/INC/2026/TEST-84729, 15/01/2026, ₹1,80,000 family income, Gujarat, Ahmedabad, SC, Mamlatdar Office.
  2. test_b_multi_page.pdf: 4 pages with facts strictly segregated:
     Page 1: Name, Certificate Number
     Page 2: Family Income = ₹1,80,000
     Page 3: Father Income = ₹1,20,000, Mother Income = ₹60,000
     Page 4: Address, Category = SC, Issuing Authority = Mamlatdar Office
  3. test_c_income_distinction.pdf: Pure family & parental income breakdown with NO personal income.
  4. test_d_scanned.pdf: Scanned raster image PDF (empty text layer) with OCR fallback verification.
"""

from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageDraw

FIXTURES_DIR = Path(__file__).resolve().parent


def create_test_a():
    """TEST A: Single-page certificate with all required fields on Page 1."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = (
        "GOVERNMENT OF GUJARAT\n"
        "REVENUE DEPARTMENT - MAMLATDAR OFFICE\n"
        "ANNUAL INCOME CERTIFICATE\n\n"
        "Certificate Number: TEST/GJ/INC/2026/TEST-84729\n"
        "Date of Issue: 15/01/2026\n\n"
        "This is to certify that Shri Aarav Patel,\n"
        "resident of 24, Shantivan Residency, Ahmedabad, Gujarat,\n"
        "has a total annual family income of Rs. 1,80,000\n"
        "(Rupees One Lakh Eighty Thousand only) from all combined household sources.\n\n"
        "Social Category: SC\n"
        "Issuing Authority: Mamlatdar Office, Ahmedabad, Gujarat\n"
    )
    page.insert_text((50, 80), text, fontsize=12)
    out_path = FIXTURES_DIR / "test_a_single_page.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Created {out_path}")


def create_test_b():
    """TEST B: 4-page document with facts strictly partitioned across pages 1 to 4."""
    doc = fitz.open()

    # Page 1: Applicant Name & Certificate Number ONLY
    p1 = doc.new_page(width=595, height=842)
    t1 = (
        "GOVERNMENT OF GUJARAT - REVENUE DEPARTMENT\n"
        "CITIZEN VERIFICATION DOSSIER - PART 1: IDENTIFICATION\n\n"
        "Applicant Full Name: Aarav Patel\n"
        "Certificate Number: TEST/GJ/INC/2026/TEST-84729\n"
        "Date of Issue: 15/01/2026\n\n"
        "Note: Detailed financial assessments and demographic categories are on subsequent schedules.\n"
    )
    p1.insert_text((50, 80), t1, fontsize=12)

    # Page 2: Total Annual Family Income = ₹1,80,000 ONLY
    p2 = doc.new_page(width=595, height=842)
    t2 = (
        "SCHEDULE A: HOUSEHOLD FINANCIAL ASSESSMENT\n\n"
        "Statutory determination of consolidated household earnings:\n\n"
        "Total Annual Family Income: Rs. 1,80,000\n"
        "(Rupees One Lakh Eighty Thousand only per annum)\n\n"
        "Evaluation Method: Revenue field inspection and tax verification.\n"
    )
    p2.insert_text((50, 80), t2, fontsize=12)

    # Page 3: Father income = ₹1,20,000, Mother income = ₹60,000
    p3 = doc.new_page(width=595, height=842)
    t3 = (
        "SCHEDULE B: EARNER CONTRIBUTIONS AND OCCUPATION BREAKDOWN\n\n"
        "Household earner breakdown records:\n\n"
        "1. Father's Employment Income: Rs. 1,20,000 per annum (Local clerical assistance)\n"
        "2. Mother's Self-Employment Income: Rs. 60,000 per annum (Tailoring and handicrafts)\n\n"
        "Personal income of applicant: Not provided / student dependent.\n"
    )
    p3.insert_text((50, 80), t3, fontsize=12)

    # Page 4: Address, Category = SC, Issuing Authority = Mamlatdar Office
    p4 = doc.new_page(width=595, height=842)
    t4 = (
        "SCHEDULE C: JURISDICTION, DEMOGRAPHICS & DISPATCH\n\n"
        "Residential Address: 24, Shantivan Residency, Ahmedabad, Gujarat\n"
        "State of Domicile: Gujarat\n"
        "District: Ahmedabad\n"
        "Social Category: SC\n\n"
        "Issuing Authority: Mamlatdar Office, Ahmedabad\n"
        "Authorized Signatory: Competent Revenue Officer\n"
    )
    p4.insert_text((50, 80), t4, fontsize=12)

    out_path = FIXTURES_DIR / "test_b_multi_page.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Created {out_path}")


def create_test_c():
    """TEST C: Personal vs Family Income distinction test document."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = (
        "GOVERNMENT OF GUJARAT\n"
        "HOUSEHOLD INCOME STATEMENT\n\n"
        "Certificate Reference: TEST/GJ/INC/2026/TEST-84729\n"
        "Applicant: Aarav Patel (Dependent Student - No Personal Income)\n"
        "Personal Income: NOT PROVIDED / NIL\n\n"
        "Contributing Earners:\n"
        "- Father's Employment Income: Rs. 1,20,000 per annum\n"
        "- Mother's Self-Employment Income: Rs. 60,000 per annum\n\n"
        "Total Annual Family Income: Rs. 1,80,000\n"
        "Issuing Authority: Mamlatdar Office\n"
    )
    page.insert_text((50, 80), text, fontsize=12)
    out_path = FIXTURES_DIR / "test_c_income_distinction.pdf"
    doc.save(str(out_path))
    doc.close()
    print(f"Created {out_path}")


def create_test_d():
    """TEST D: Scanned PDF (Pure raster image, empty digital text layer, with OCR fallback annotation)."""
    img = Image.new("RGB", (650, 450), color=(250, 250, 240))
    draw = ImageDraw.Draw(img)
    text = (
        "GOVERNMENT OF GUJARAT\n"
        "SCANNED CERTIFICATE OF INCOME\n\n"
        "Certificate Number: TEST/GJ/INC/2026/TEST-84729\n"
        "Applicant Name: Aarav Patel\n"
        "Total Annual Family Income: Rs. 1,80,000\n"
        "Category: SC\n"
        "State: Gujarat\n"
        "District: Ahmedabad\n"
        "Issuing Authority: Mamlatdar Office\n"
    )
    draw.text((30, 30), text, fill=(15, 15, 15))
    temp_img_path = FIXTURES_DIR / "temp_scanned_d.png"
    img.save(str(temp_img_path))

    doc = fitz.open()
    page = doc.new_page(width=650, height=450)
    # Insert raster image taking up the whole page (no digital text layer)
    page.insert_image(fitz.Rect(0, 0, 650, 450), filename=str(temp_img_path))
    # Add OCR text annotation
    annot = page.add_text_annot(fitz.Point(30, 30), text)
    annot.set_info(content=text)
    annot.update()

    out_path = FIXTURES_DIR / "test_d_scanned.pdf"
    doc.save(str(out_path))
    doc.close()
    temp_img_path.unlink()
    print(f"Created {out_path}")


if __name__ == "__main__":
    create_test_a()
    create_test_b()
    create_test_c()
    create_test_d()
