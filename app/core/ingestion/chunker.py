import re
from langchain_text_splitters import RecursiveCharacterTextSplitter


CLAUSE_HEADING_RE = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)*[\)\.]?\s+.+|"          # 1. Term / 4.2 Payment
    r"[A-Z][A-Z\s,&/\-]{4,}|"               # TERMINATION / GOVERNING LAW
    r"(?:Section|Clause|Article)\s+\d+[A-Za-z0-9.\-]*[:\-]?\s+.+"
    r")$"
)

DEFINED_TERM_RE = re.compile(r'"([^"]{2,80})"|\'([A-Z][A-Za-z0-9\s\-]{1,60})\'')
PARTY_ENTITY_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.,\- ]{1,80}\s(?:Inc\.|LLC|Ltd\.|Limited|Corporation|Corp\.|Company|Co\.|LP|LLP|PLC))\b"
)


def _iter_segments(text: str):
    lines = text.splitlines()
    segments = []
    current_heading = None
    current_lines = []
    cursor = 0
    segment_start = 0

    for raw_line in lines:
        line = raw_line.strip()
        line_start = cursor
        cursor += len(raw_line) + 1

        if not line:
            if current_lines:
                current_lines.append("")
            continue

        if CLAUSE_HEADING_RE.match(line):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    segments.append({
                        "heading": current_heading,
                        "text": body,
                        "start_char": segment_start,
                    })
            current_heading = line
            current_lines = [line]  # KEEP heading in actual text content
            segment_start = line_start
            continue

        if not current_lines:
            segment_start = line_start
        current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            segments.append({
                "heading": current_heading,
                "text": body,
                "start_char": segment_start,
            })

    if not segments and text.strip():
        segments.append({
            "heading": None,
            "text": text.strip(),
            "start_char": 0,
        })

    return segments


def _extract_defined_terms(text: str):
    terms = []
    for match in DEFINED_TERM_RE.finditer(text):
        term = (match.group(1) or match.group(2) or "").strip()
        if term and term not in terms:
            terms.append(term)
    return terms[:10]


def _extract_party_mentions(text: str):
    parties = []
    for match in PARTY_ENTITY_RE.finditer(text):
        party = match.group(1).strip()
        if party not in parties:
            parties.append(party)
    return parties[:5]


def _page_for_offset(page_spans, offset: int):
    for page in page_spans or []:
        if page["start_char"] <= offset <= page["end_char"] + 2:
            return page["page_number"]
    return 1


def _build_metadata(document_id: str, chunk_id: int, heading: str | None, chunk_text: str, start_char: int, page_spans):
    return {
        "source": document_id,
        "chunk_id": chunk_id,
        "page_number": _page_for_offset(page_spans, start_char),
        "section_heading": heading or "",
        "clause_title": heading or "",
        "clause_type": "",
        "party_mentions": _extract_party_mentions(chunk_text),
        "defined_terms": _extract_defined_terms(chunk_text),
        "start_char": start_char,
        "end_char": start_char + len(chunk_text),
    }


def chunk_text(text: str, document_id: str, page_spans=None):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=120,
        separators=["\n\n", "\n", ". ", "; ", " "],
    )

    structured_chunks = []
    chunk_id = 0

    for segment in _iter_segments(text):
        heading = segment["heading"]
        segment_text = segment["text"]
        segment_start = segment["start_char"]

        if len(segment_text) <= 900:
            parts = [segment_text]
        else:
            parts = splitter.split_text(segment_text)

        local_cursor = 0
        for part in parts:
            stripped_part = part.strip()
            if not stripped_part:
                continue

            relative_offset = segment_text.find(stripped_part, local_cursor)
            if relative_offset == -1:
                relative_offset = local_cursor
            absolute_start = segment_start + relative_offset
            local_cursor = relative_offset + len(stripped_part)

            structured_chunks.append({
                "content": stripped_part,
                "metadata": _build_metadata(
                    document_id=document_id,
                    chunk_id=chunk_id,
                    heading=heading,
                    chunk_text=stripped_part,
                    start_char=absolute_start,
                    page_spans=page_spans,
                ),
            })
            chunk_id += 1

    return structured_chunks
