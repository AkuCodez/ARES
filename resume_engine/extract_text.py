# resume_engine/extract_text.py

from pathlib import Path
import fitz  # PyMuPDF
import docx  # python-docx

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract plain text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()


def extract_text_from_docx(docx_path: str) -> str:
    """
    Extract plain text from a .docx file.
    Captures paragraphs AND table cell contents (resumes often
    put contact info / skills inside tables).
    """
    document = docx.Document(docx_path)
    parts = []

    # Paragraphs
    for para in document.paragraphs:
        if para.text.strip():
            parts.append(para.text)

    # Tables (skills grids, contact info blocks, etc.)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    parts.append(cell_text)

    return "\n".join(parts).strip()


def extract_resume_text(file_path: str) -> str:
    """
    Unified entry point — dispatches to the correct extractor
    based on the file extension.

    Raises:
        ValueError: if the file extension is not supported.
        FileNotFoundError: if the file does not exist.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(str(path))
    if ext == ".docx":
        return extract_text_from_docx(str(path))

    raise ValueError(
        f"Unsupported resume format: '{ext}'. "
        f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )