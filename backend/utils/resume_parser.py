import re
import pdfplumber


def parse_resume_pdf(file_path: str) -> str:
    """
    Extract and clean text from a PDF resume file.

    Args:
        file_path: Absolute path to the PDF file.

    Returns:
        Cleaned text content of the PDF, or empty string on failure.
    """
    try:
        extracted_pages: list[str] = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)

        raw_text = "\n".join(extracted_pages)

        # Normalize unicode whitespace characters to regular spaces
        raw_text = raw_text.replace("\xa0", " ").replace("​", "")

        # Collapse runs of spaces/tabs (but preserve newlines)
        raw_text = re.sub(r"[ \t]+", " ", raw_text)

        # Collapse more than two consecutive newlines into two
        raw_text = re.sub(r"\n{3,}", "\n\n", raw_text)

        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in raw_text.splitlines()]
        cleaned = "\n".join(lines)

        # Final strip of leading/trailing whitespace from the whole block
        return cleaned.strip()

    except Exception:
        return ""
