"""Document loading and engineering-aware chunking.

Excel/CSV: one meaningful row = one complete engineering chunk (DFMEA row,
DVP&R row, or lesson), preserving file/sheet/row metadata for citations.
MD/TXT: word-window chunks with overlap. PDF/DOCX: optional (pypdf/python-docx),
skipped gracefully if the library is not installed.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd

from .store import chunk_hash

CHUNK_WORDS = 220          # ~ 500-1000 token guidance scaled to words
CHUNK_OVERLAP_WORDS = 40

# Columns used to build readable chunk text from spreadsheet rows, in priority order.
_PREFERRED_COLUMNS = [
    "Component", "Component Name", "Item", "Function",
    "Failure Mode", "Potential Failure Mode", "Effect", "Potential Effect of Failure",
    "Cause", "Potential Cause / Mechanism", "Prevention Control", "Detection Control",
    "Recommended Action", "Severity", "Occurrence", "Detection", "RPN", "Risk Category",
    "Test ID", "Recommended Validation Test", "Validation Type", "Validation Level",
    "Test Objective", "Acceptance Criteria", "Responsible Team", "Build Phase",
    "Lesson Learned", "Lesson Summary", "Prior Issue", "Recommended Consideration",
    "Recommended Preventive Action", "Requirement ID", "Failure Mode ID",
    "Linked Failure Mode", "Linked Failure Mode ID", "Standard Reference", "Notes",
]


def _row_to_text(row: pd.Series, document_type: str) -> str:
    parts = [f"Document Type: {document_type}"]
    used = set()
    for col in _PREFERRED_COLUMNS:
        if col in row.index and str(row[col]).strip() not in ("", "nan", "None"):
            parts.append(f"{col}: {row[col]}")
            used.add(col)
    # include any remaining short informative fields
    for col in row.index:
        if col in used:
            continue
        value = str(row[col]).strip()
        if value and value.lower() not in ("nan", "none", "tbd") and len(value) < 200:
            parts.append(f"{col}: {value}")
    return "\n".join(parts)


def _row_meta_value(row: pd.Series, *names: str) -> str:
    for name in names:
        if name in row.index and str(row[name]).strip() not in ("", "nan", "None"):
            return str(row[name]).strip()
    return ""


def _text_metadata(text: str) -> dict[str, str]:
    """Extract common engineering labels from free-text documents.

    Text chunks previously discarded explicit labels such as ``Component:``.
    Preserving them lets the retriever identify cross-component conflicts using
    metadata instead of relying only on token similarity.
    """
    aliases = {
        "component_name": ("component", "component name", "item"),
        "failure_mode_id": ("failure mode id", "linked failure mode id"),
        "failure_mode": ("failure mode", "potential failure mode", "linked failure mode"),
        "test_id": ("test id",),
        "requirement_id": ("requirement id",),
        "risk_category": ("risk category",),
    }
    found: dict[str, str] = {key: "" for key in aliases}
    for key, labels in aliases.items():
        for label in labels:
            match = re.search(
                rf"(?im)^\s*(?:[-*]\s*)?{re.escape(label)}\s*:\s*(.+?)\s*$",
                text,
            )
            if match:
                found[key] = match.group(1).strip()
                break
    return found


def chunk_dataframe_rows(
    df: pd.DataFrame,
    file_name: str,
    sheet_name: str,
    document_type: str,
    source_strength: str,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for row_number, (_, row) in enumerate(df.iterrows(), start=2):  # +header row, 1-based
        text = _row_to_text(row, document_type)
        if len(text) < 60:  # skip empty / meaningless rows
            continue
        chunks.append(
            {
                "chunk_id": chunk_hash(file_name, sheet_name, row_number, text),
                "chunk_text": text,
                "metadata": {
                    "file_name": file_name,
                    "sheet_name": sheet_name,
                    "row_number": row_number,
                    "document_type": document_type,
                    "source_strength": source_strength,
                    "component_name": _row_meta_value(row, "Component", "Component Name", "Item"),
                    "failure_mode_id": _row_meta_value(row, "Failure Mode ID", "Linked Failure Mode ID"),
                    "failure_mode": _row_meta_value(row, "Failure Mode", "Potential Failure Mode", "Linked Failure Mode"),
                    "test_id": _row_meta_value(row, "Test ID"),
                    "requirement_id": _row_meta_value(row, "Requirement ID"),
                    "risk_category": _row_meta_value(row, "Risk Category"),
                },
            }
        )
    return chunks


def chunk_text_document(
    text: str,
    file_name: str,
    document_type: str,
    source_strength: str,
) -> list[dict[str, Any]]:
    words = text.split()
    document_metadata = _text_metadata(text)
    chunks: list[dict[str, Any]] = []
    start, index = 0, 1
    while start < len(words):
        window = words[start : start + CHUNK_WORDS]
        chunk_text = " ".join(window)
        if len(chunk_text.strip()) >= 80:
            stored_text = f"Document Type: {document_type}\n{chunk_text}"
            chunks.append(
                {
                    "chunk_id": chunk_hash(file_name, "text", index, stored_text),
                    "chunk_text": stored_text,
                    "metadata": {
                        "file_name": file_name,
                        "sheet_name": "text",
                        "row_number": index,
                        "document_type": document_type,
                        "source_strength": source_strength,
                        **document_metadata,
                    },
                }
            )
            index += 1
        if start + CHUNK_WORDS >= len(words):
            break
        start += CHUNK_WORDS - CHUNK_OVERLAP_WORDS
    return chunks


def load_file_to_chunks(
    path: str | Path,
    document_type: str,
    source_strength: str,
    file_bytes: bytes | None = None,
) -> list[dict[str, Any]]:
    """Parse a file into chunks. Supports xlsx, csv, md, txt (pdf/docx optional)."""
    path = Path(path)
    suffix = path.suffix.lower()
    name = path.name

    if suffix in (".xlsx", ".xlsm"):
        source: Any = pd.ExcelFile(file_bytes and __import__("io").BytesIO(file_bytes) or path)
        chunks: list[dict[str, Any]] = []
        for sheet in source.sheet_names:
            df = source.parse(sheet).astype(str)
            chunks.extend(chunk_dataframe_rows(df, name, sheet, document_type, source_strength))
        return chunks
    if suffix == ".csv":
        df = pd.read_csv(file_bytes and __import__("io").BytesIO(file_bytes) or path).astype(str)
        return chunk_dataframe_rows(df, name, "csv", document_type, source_strength)
    if suffix in (".md", ".txt"):
        text = file_bytes.decode("utf-8", errors="ignore") if file_bytes else path.read_text(errors="ignore")
        return chunk_text_document(text, name, document_type, source_strength)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return []
        reader = PdfReader(file_bytes and __import__("io").BytesIO(file_bytes) or str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return chunk_text_document(text, name, document_type, source_strength)
    if suffix == ".docx":
        try:
            import docx
        except ImportError:
            return []
        document = docx.Document(file_bytes and __import__("io").BytesIO(file_bytes) or str(path))
        text = "\n".join(p.text for p in document.paragraphs)
        return chunk_text_document(text, name, document_type, source_strength)
    return []
