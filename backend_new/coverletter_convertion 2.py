from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
import pathlib

def read_text(path: str) -> str:
    """Read text file safely."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:
            return f.read().strip()

def set_margins(section, top=1.0, bottom=1.0, left=1.0, right=1.0):
    section.top_margin = Inches(top)
    section.bottom_margin = Inches(bottom)
    section.left_margin = Inches(left)
    section.right_margin = Inches(right)

def style_base(doc: Document):
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    font.size = Pt(11)

def convert_cover_letter(input_file, output_file):
    doc = Document()
    style_base(doc)
    set_margins(doc.sections[0])

    text = read_text(input_file)

    # Split into paragraphs by double newlines
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    for para in paragraphs:
        p = doc.add_paragraph(para)
        p.paragraph_format.space_after = Pt(12)

    out = pathlib.Path(output_file).expanduser().resolve()
    doc.save(out)
    print(f"[✔] Cover letter saved to: {out}")

if __name__ == "__main__":
    convert_cover_letter("cover_letter_4231348713.txt", "cover_letter_4231348713.docx")
