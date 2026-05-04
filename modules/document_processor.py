"""
modules/document_processor.py
Handles PDF and image text extraction using pdfplumber + pytesseract OCR.
"""

import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io
import re


def extract_text_from_pdf(file_bytes: bytes, filename: str) -> dict:
    """
    Extract text from a PDF file.
    Tries pdfplumber first (digital PDFs), falls back to OCR (scanned PDFs).
    Returns: { "full_text": str, "pages": [ {"page": int, "text": str} ] }
    """
    pages_data = []
    full_text_parts = []

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                text = page.extract_text() or ""

                # If page has very little text, use OCR
                if len(text.strip()) < 50:
                    text = _ocr_page(file_bytes, page_num)

                pages_data.append({"page": page_num, "text": text.strip()})
                full_text_parts.append(f"[Page {page_num}]\n{text.strip()}")

    except Exception as e:
        # Fallback: full OCR
        try:
            ocr_pages = _ocr_all_pages(file_bytes)
            pages_data = ocr_pages
            full_text_parts = [f"[Page {p['page']}]\n{p['text']}" for p in ocr_pages]
        except Exception as ocr_err:
            return {
                "full_text": "",
                "pages": [],
                "error": f"Extraction failed: {str(e)} | OCR fallback failed: {str(ocr_err)}"
            }

    return {
        "full_text": "\n\n".join(full_text_parts),
        "pages": pages_data,
        "filename": filename,
        "total_pages": len(pages_data)
    }


def extract_text_from_image(file_bytes: bytes, filename: str) -> dict:
    """
    Extract text from an image file using pytesseract OCR.
    """
    try:
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image, config='--psm 6')
        return {
            "full_text": text.strip(),
            "pages": [{"page": 1, "text": text.strip()}],
            "filename": filename,
            "total_pages": 1
        }
    except Exception as e:
        return {
            "full_text": "",
            "pages": [],
            "filename": filename,
            "total_pages": 0,
            "error": str(e)
        }


def _ocr_page(file_bytes: bytes, page_num: int) -> str:
    """OCR a specific page of a PDF."""
    try:
        images = convert_from_bytes(file_bytes, first_page=page_num, last_page=page_num, dpi=200)
        if images:
            text = pytesseract.image_to_string(images[0], config='--psm 6')
            return text.strip()
    except Exception:
        pass
    return ""


def _ocr_all_pages(file_bytes: bytes) -> list:
    """OCR all pages of a PDF."""
    pages = []
    try:
        images = convert_from_bytes(file_bytes, dpi=200)
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, config='--psm 6')
            pages.append({"page": i + 1, "text": text.strip()})
    except Exception:
        pages = [{"page": 1, "text": ""}]
    return pages


def clean_text(text: str) -> str:
    """Basic text cleanup."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def truncate_text(text: str, max_chars: int = 12000) -> str:
    """Truncate text to fit within LLM context limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated for length]..."
