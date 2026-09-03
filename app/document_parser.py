"""Extract plain text from uploaded source documents."""

from __future__ import annotations

import io
import logging
from typing import BinaryIO

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
logger = logging.getLogger(__name__)


def extract_text(filename: str, file_obj: BinaryIO) -> str:
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    data = file_obj.read()

    if ext in {".txt", ".md"}:
        return data.decode("utf-8", errors="replace").strip()

    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages).strip()
        except ValueError:
            raise
        except Exception as exc:
            logger.exception("PDF parse failed for %s", filename)
            raise ValueError("Could not read PDF. The file may be corrupt or encrypted.") from exc
        if not text:
            raise ValueError("Could not extract text from PDF")
        return text

    if ext == ".docx":
        try:
            from docx import Document

            doc = Document(io.BytesIO(data))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs).strip()
        except ValueError:
            raise
        except Exception as exc:
            logger.exception("DOCX parse failed for %s", filename)
            raise ValueError("Could not read DOCX. The file may be corrupt.") from exc
        if not text:
            raise ValueError("Could not extract text from DOCX")
        return text

    raise ValueError(f"Unsupported file type: {ext}")
