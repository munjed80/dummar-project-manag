"""
OCR Service Abstraction Layer.

Provides a pluggable OCR interface. The default implementation uses
basic text extraction from PDFs (via pdfplumber if available) and
Pillow for images. The architecture allows swapping in Tesseract,
Google Vision, or any other OCR engine by implementing OcrEngine.

Status: Partial — full OCR (Tesseract, cloud APIs) requires
additional system packages not available in all environments.
The text-extraction foundation is fully functional.
"""

import io
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("dummar.ocr")


@dataclass
class OcrResult:
    """Standardized result from any OCR engine."""
    text: str = ""
    confidence: float = 0.0
    engine: str = "none"
    page_count: int = 0
    warnings: list = field(default_factory=list)
    success: bool = False


class OcrEngine(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def extract_text(self, file_path: str, file_type: str) -> OcrResult:
        """Extract text from a file. Returns OcrResult."""
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class BasicTextExtractor(OcrEngine):
    """
    Basic text extraction engine.
    - PDFs: extracts embedded text layers (not scanned images).
    - Text/CSV files: reads content directly.
    - Images: returns placeholder (requires Tesseract for real OCR).
    
    This is the safe, always-available first implementation.
    """

    def name(self) -> str:
        return "basic_text_extractor"

    def extract_text(self, file_path: str, file_type: str) -> OcrResult:
        if not os.path.exists(file_path):
            return OcrResult(
                text="",
                confidence=0.0,
                engine=self.name(),
                success=False,
                warnings=["File not found"],
            )

        file_type = (file_type or "").lower().strip(".")

        try:
            if file_type == "pdf":
                return self._extract_pdf(file_path)
            elif file_type in ("txt", "text"):
                return self._extract_text_file(file_path)
            elif file_type in ("csv",):
                return self._extract_text_file(file_path)
            elif file_type in ("jpg", "jpeg", "png", "tiff", "tif", "bmp"):
                return self._extract_image(file_path)
            else:
                return OcrResult(
                    text="",
                    confidence=0.0,
                    engine=self.name(),
                    success=False,
                    warnings=[f"Unsupported file type: {file_type}"],
                )
        except Exception as e:
            logger.exception("OCR extraction failed for %s", file_path)
            return OcrResult(
                text="",
                confidence=0.0,
                engine=self.name(),
                success=False,
                warnings=[f"Extraction error: {str(e)}"],
            )

    def _extract_pdf(self, file_path: str) -> OcrResult:
        """Extract text from PDF using PyPDF2 or basic binary parsing."""
        text = ""
        page_count = 0
        warnings = []

        # Try PyPDF2 first
        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                page_count = len(reader.pages)
                pages_text = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    pages_text.append(page_text)
                text = "\n\n".join(pages_text)
        except ImportError:
            warnings.append("PyPDF2 not available — trying basic extraction")
            text, page_count = self._basic_pdf_extract(file_path)
        except Exception as e:
            warnings.append(f"PyPDF2 extraction failed: {str(e)}")
            text, page_count = self._basic_pdf_extract(file_path)

        # Calculate confidence based on text content
        confidence = self._estimate_confidence(text)

        if not text.strip():
            warnings.append(
                "No text extracted — PDF may be scanned image. "
                "Full OCR (Tesseract) needed for image-based PDFs."
            )
            confidence = 0.0

        return OcrResult(
            text=text.strip(),
            confidence=confidence,
            engine=self.name(),
            page_count=page_count,
            warnings=warnings,
            success=bool(text.strip()),
        )

    def _basic_pdf_extract(self, file_path: str) -> tuple:
        """Fallback: read raw bytes and try to find text streams."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            # Very basic: find text between BT and ET markers
            text_parts = []
            # Try to decode readable portions
            try:
                decoded = content.decode("latin-1", errors="ignore")
                # Find parenthesized text in PDF streams
                for match in re.finditer(r"\(([^)]{2,})\)", decoded):
                    part = match.group(1)
                    if any(c.isalpha() for c in part):
                        text_parts.append(part)
            except Exception:
                pass
            return " ".join(text_parts), 0
        except Exception:
            return "", 0

    def _extract_text_file(self, file_path: str) -> OcrResult:
        """Read plain text or CSV file content."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            return OcrResult(
                text=text.strip(),
                confidence=1.0,
                engine=self.name(),
                page_count=1,
                success=True,
            )
        except Exception as e:
            return OcrResult(
                text="",
                confidence=0.0,
                engine=self.name(),
                success=False,
                warnings=[f"Text read failed: {str(e)}"],
            )

    def _extract_image(self, file_path: str) -> OcrResult:
        """
        Image OCR — requires Tesseract (pytesseract).
        Returns partial result if Tesseract is not installed.
        """
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(file_path)
            # Support Arabic + English
            text = pytesseract.image_to_string(img, lang="ara+eng")
            confidence = self._estimate_confidence(text)
            return OcrResult(
                text=text.strip(),
                confidence=confidence,
                engine="tesseract",
                page_count=1,
                success=bool(text.strip()),
            )
        except ImportError:
            return OcrResult(
                text="",
                confidence=0.0,
                engine=self.name(),
                success=False,
                warnings=[
                    "Tesseract/pytesseract not installed. "
                    "Image OCR requires: pip install pytesseract + system tesseract-ocr"
                ],
            )
        except Exception as e:
            return OcrResult(
                text="",
                confidence=0.0,
                engine=self.name(),
                success=False,
                warnings=[f"Image OCR failed: {str(e)}"],
            )

    @staticmethod
    def _estimate_confidence(text: str) -> float:
        """Estimate text quality based on content heuristics."""
        if not text or not text.strip():
            return 0.0
        # Count meaningful characters vs noise
        total = len(text)
        alpha_numeric = sum(1 for c in text if c.isalnum() or c in " \n\t.,;:!?/-")
        ratio = alpha_numeric / total if total > 0 else 0
        # Penalize very short text
        length_factor = min(1.0, len(text.strip()) / 100)
        return round(min(1.0, ratio * length_factor), 3)


# --- Singleton service ---

_engine: Optional[OcrEngine] = None


def get_ocr_engine() -> OcrEngine:
    """Get the configured OCR engine (singleton)."""
    global _engine
    if _engine is None:
        _engine = BasicTextExtractor()
    return _engine


def set_ocr_engine(engine: OcrEngine):
    """Replace the OCR engine (for testing or future upgrades)."""
    global _engine
    _engine = engine


def process_ocr(file_path: str, file_type: str) -> OcrResult:
    """Convenience function to run OCR on a file."""
    engine = get_ocr_engine()
    return engine.extract_text(file_path, file_type)
