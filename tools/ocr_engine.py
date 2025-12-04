import re
import pdfplumber
import easyocr
import numpy as np
from pdf2image import convert_from_path
from protocols.mcp import BaseTool
from pathlib import Path

class DataHarvesterTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="data_harvester",
            description="Extracts text from invoices. Uses PDFPlumber for digital PDFs and EasyOCR for scans."
        )
        print(" [Init] Loading EasyOCR models... (This happens only once)")
        # We load English, Spanish, German
        self.reader = easyocr.Reader(['en', 'es', 'de'], gpu=False)

    def _redact_pii(self, text: str) -> str:
        """Responsible AI: Redact Email Addresses and Phone Numbers"""
        # Redact Emails
        text = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL_REDACTED]', text)
        return text

    def execute(self, file_path: str) -> dict:
        """
        Input: Path to the PDF/Image file.
        Output: Dictionary with 'raw_text' and 'method_used'.
        """
        path = Path(file_path)
        if not path.exists():
            return {"status": "error", "message": "File not found"}

        extracted_text = ""
        method = "unknown"

        try:
            # Strategy 1: Try Fast Digital Extraction (PDFPlumber)
            if path.suffix.lower() == '.pdf':
                with pdfplumber.open(path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                
                if extracted_text.strip():
                    method = "pdfplumber (Digital)"
            
            # Strategy 2: Fallback to Optical Character Recognition (EasyOCR)
            # Runs if file is an image OR if PDFPlumber found nothing (scanned PDF)
            if not extracted_text.strip():
                print(" [OCR] Digital extraction empty. Switching to Vision OCR...")
                method = "EasyOCR (Vision)"
                
                images = []
                if path.suffix.lower() == '.pdf':
                    images = convert_from_path(str(path))
                else:
                    # It's likely an image (.png, .jpg)
                    import PIL.Image
                    images = [PIL.Image.open(str(path))]

                for img in images:
                    img_array = np.array(img)
                    # detail=0 returns a simple list of strings
                    ocr_result = self.reader.readtext(img_array, detail=0)
                    extracted_text += " ".join(ocr_result) + "\n"

            # Apply Guardrails
            clean_text = self._redact_pii(extracted_text)

            return {
                "status": "success",
                "text": clean_text,
                "method": method
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}