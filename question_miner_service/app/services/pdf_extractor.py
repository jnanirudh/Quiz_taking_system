from io import BytesIO

from pypdf import PdfReader


class PdfExtractor:
    def extract_text(self, pdf_bytes: bytes) -> str:
        reader = PdfReader(BytesIO(pdf_bytes))
        extracted_pages: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            page_text = page_text.strip()
            if page_text:
                extracted_pages.append(page_text)

        return "\n\n".join(extracted_pages).strip()
