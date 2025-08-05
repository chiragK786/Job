from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

# Define unwanted phrases to remove
removal_phrases = [
    "Shared by Job Curator", "Join us on Telegram",
    "This document is for Subscribed Members only",
    "report to us on info@jobcurator.in", "https://t.me/",
    "mailto:info@jobcurator.in", "Job Curator", "Telegram"
]


def create_clean_page(text):
    """Generates a single PDF page with cleaned text using ReportLab."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40

    for line in text.split('\n'):
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(40, y, line[:100])  # Avoid overly long lines
        y -= 14

    c.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def clean_pdf(input_pdf_path, output_pdf_path):
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue

        lines = text.splitlines()
        cleaned_lines = [line for line in lines if not any(phrase in line for phrase in removal_phrases)]
        cleaned_text = "\n".join(cleaned_lines)

        clean_page = create_clean_page(cleaned_text)
        writer.add_page(clean_page)

    with open(output_pdf_path, 'wb') as f:
        writer.write(f)

    print(f"Cleaned PDF saved to: {output_pdf_path}")


# === Usage ===
input_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/TestingJobs_FullList.pdf"  # Replace with your input file path
output_path = "TestingJobs_Cleaned.pdf"  # Replace with your desired output file path

clean_pdf(input_path, output_path)
