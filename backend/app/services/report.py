from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

def build_report(title: str, sections: list[tuple[str, list[str]]]) -> BytesIO:
    b = BytesIO()
    doc = SimpleDocTemplate(b, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    styles['Title'].alignment = TA_LEFT
    styles['BodyText'].fontSize = 9
    styles['BodyText'].leading = 12
    story = [Paragraph(title, styles['Title']), Spacer(1, 12)]
    for heading, lines in sections:
        story.append(Paragraph(heading, styles['Heading2']))
        for line in lines:
            story.append(Paragraph(str(line).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'), styles['BodyText']))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))
    doc.build(story)
    b.seek(0)
    return b
