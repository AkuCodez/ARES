import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()

def extract_text_from_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if not text.strip():
        raise ValueError("Could not extract text from DOCX. File may be empty.")
    return text


def extract_text(path: str) -> str:
    """Universal entry point — detects PDF or DOCX automatically."""
    if path.lower().endswith(".docx"):
        return extract_text_from_docx(path)
    return extract_text_from_pdf(path)