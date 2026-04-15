import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.core.config import settings


def generate_contract_pdf(contract) -> str:
    """Generate a PDF summary for a contract and return the file path."""
    pdf_dir = os.path.join(settings.UPLOAD_DIR, "contracts", "pdf")
    os.makedirs(pdf_dir, exist_ok=True)

    filename = f"contract_{contract.contract_number.replace('/', '_')}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 2 * cm, "Contract Summary")

    # Contract details
    c.setFont("Helvetica", 12)
    y = height - 4 * cm
    line_height = 0.7 * cm

    details = [
        ("Contract Number:", str(contract.contract_number)),
        ("Title:", str(contract.title)),
        ("Contractor:", str(contract.contractor_name)),
        ("Contact:", str(contract.contractor_contact or "N/A")),
        ("Type:", str(contract.contract_type.value if hasattr(contract.contract_type, 'value') else contract.contract_type)),
        ("Value:", f"{contract.contract_value:,.2f} SYP"),
        ("Start Date:", str(contract.start_date)),
        ("End Date:", str(contract.end_date)),
        ("Duration:", f"{contract.execution_duration_days or 'N/A'} days"),
        ("Status:", str(contract.status.value if hasattr(contract.status, 'value') else contract.status)),
        ("Related Areas:", str(contract.related_areas or "N/A")),
    ]

    for label, value in details:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 11)
        c.drawString(7 * cm, y, value)
        y -= line_height

    # Scope description
    y -= line_height
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Scope Description:")
    y -= line_height
    c.setFont("Helvetica", 10)

    scope = str(contract.scope_description or "")
    # Simple text wrapping
    max_width = width - 4 * cm
    words = scope.split()
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        if c.stringWidth(test_line, "Helvetica", 10) < max_width:
            line = test_line
        else:
            c.drawString(2 * cm, y, line)
            y -= line_height
            line = word
            if y < 3 * cm:
                c.showPage()
                y = height - 2 * cm
    if line:
        c.drawString(2 * cm, y, line)

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, 1.5 * cm, "Dummar Project Management - Damascus, Syria")

    c.save()

    with open(filepath, "wb") as f:
        f.write(buffer.getvalue())

    return f"/uploads/contracts/pdf/{filename}"
