from pypdf import PdfReader
import docx


def _append_page(pages, page_number: int, text: str, cursor: int):
    page_text = text or ""
    start = cursor
    end = start + len(page_text)
    pages.append({
        "page_number": page_number,
        "text": page_text,
        "start_char": start,
        "end_char": end,
    })
    return end


def parse_pdf(file_path: str) -> dict:
    reader = PdfReader(file_path)
    pages = []
    full_text_parts = []
    cursor = 0

    for idx, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        full_text_parts.append(page_text)
        cursor = _append_page(pages, idx, page_text, cursor)
        cursor += 2  # account for the join separator below

    text = "\n\n".join(full_text_parts).strip()
    return {"text": text, "pages": pages}


def parse_docx(file_path: str) -> dict:
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs]).strip()
    return {
        "text": text,
        "pages": [{
            "page_number": 1,
            "text": text,
            "start_char": 0,
            "end_char": len(text),
        }],
    }


def parse_txt(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    return {
        "text": text,
        "pages": [{
            "page_number": 1,
            "text": text,
            "start_char": 0,
            "end_char": len(text),
        }],
    }


def parse_document(file_path: str) -> dict:
    if file_path.endswith(".pdf"):
        return parse_pdf(file_path)
    if file_path.endswith(".docx"):
        return parse_docx(file_path)
    if file_path.endswith(".txt"):
        return parse_txt(file_path)
    raise ValueError("Unsupported file format")
