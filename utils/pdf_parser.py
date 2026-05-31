"""
pdf_parser.py - PDF text extraction utility for InterviewAI
Uses PyPDF2 to extract and clean text from uploaded resume PDFs.
"""

import os
import re
import PyPDF2
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    from PIL import Image
except Exception:
    Image = None
try:
    import pytesseract
except Exception:
    pytesseract = None
from werkzeug.utils import secure_filename

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE_MB = 16  # 16 MB limit


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_pdf(filepath):
    """
    Validate that the file is a legitimate PDF.
    Returns (is_valid: bool, error_message: str)
    """
    # Check file size
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"File too large ({file_size_mb:.1f}MB). Maximum allowed is {MAX_FILE_SIZE_MB}MB."

    # Check file header (PDF magic bytes)
    try:
        with open(filepath, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                return False, "Invalid PDF file. Please upload a valid PDF resume."
    except Exception:
        return False, "Could not read the uploaded file."

    return True, ""


def extract_text_from_pdf(filepath):
    """
    Extract all text from a PDF file using PyPDF2.
    
    Args:
        filepath (str): Absolute path to the PDF file.
    
    Returns:
        str: Cleaned extracted text from the PDF.
    
    Raises:
        ValueError: If PDF is empty or cannot be read.
        Exception: For other unexpected errors.
    """
    try:
        text_parts = []

        with open(filepath, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)

            if len(reader.pages) == 0:
                raise ValueError("The PDF file appears to be empty.")

            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    print(f"Warning: Could not extract text from page {page_num + 1}: {e}")
                    continue

        if not text_parts:
            # Attempt OCR fallback for image-based PDFs using PyMuPDF + pytesseract
            ocr_text_parts = []
            if fitz is None or pytesseract is None or Image is None:
                raise ValueError("No text could be extracted from the PDF. The file may be scanned or image-based.\n"
                                 "OCR dependencies not available. Install `pymupdf`, `pytesseract`, and `Pillow`, and ensure Tesseract OCR is installed on the system.")

            # Verify tesseract binary is available
            try:
                pytesseract.get_tesseract_version()
            except Exception:
                raise ValueError("Tesseract OCR binary not found. Please install Tesseract on the host (e.g., `apt-get install -y tesseract-ocr` on Debian/Ubuntu, or install the Windows build).")

            try:
                doc = fitz.open(filepath)
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=200)
                    mode = "RGBA" if pix.alpha else "RGB"
                    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                    if mode == "RGBA":
                        img = img.convert("RGB")
                    page_text = pytesseract.image_to_string(img)
                    if page_text and page_text.strip():
                        ocr_text_parts.append(page_text)
            except Exception as e:
                raise Exception(f"OCR processing failed: {e}")

            if not ocr_text_parts:
                raise ValueError("No text could be extracted from the PDF even after OCR. The file may be corrupted or contain unreadable images.")

            raw_text = '\n'.join(ocr_text_parts)
        else:
            raw_text = '\n'.join(text_parts)
        cleaned_text = clean_resume_text(raw_text)

        return cleaned_text

    except PyPDF2.errors.PdfReadError as e:
        raise ValueError(f"Could not read PDF file: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Unexpected error reading PDF: {str(e)}")


def clean_resume_text(text):
    """
    Clean and normalize extracted resume text.
    
    - Removes excessive whitespace and blank lines
    - Normalizes line endings
    - Removes non-printable characters
    """
    if not text:
        return ""

    # Remove non-printable characters except newlines and tabs
    text = re.sub(r'[^\x20-\x7E\n\t]', ' ', text)

    # Normalize multiple spaces to single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Normalize multiple newlines to double newline (paragraph break)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]

    # Remove empty lines at start/end, keep single blank lines between sections
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        if line == '':
            if not prev_blank and cleaned_lines:
                cleaned_lines.append('')
            prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False

    return '\n'.join(cleaned_lines).strip()


def get_resume_sections(text):
    """
    Attempt to split resume text into common sections.
    Returns a dict with section names as keys.
    Useful for debugging and logging.
    """
    common_sections = [
        'education', 'experience', 'skills', 'projects',
        'certifications', 'achievements', 'objective', 'summary',
        'internship', 'work experience', 'technical skills', 'tools'
    ]

    sections = {}
    lines = text.split('\n')
    current_section = 'header'
    current_content = []

    for line in lines:
        line_lower = line.lower().strip()
        matched_section = None

        for section in common_sections:
            if section in line_lower and len(line_lower) < 50:
                matched_section = section
                break

        if matched_section:
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = matched_section
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections


def save_uploaded_file(file, upload_folder):
    """
    Securely save an uploaded file to the uploads folder.
    
    Args:
        file: Werkzeug FileStorage object
        upload_folder (str): Path to uploads directory
    
    Returns:
        tuple: (filename, filepath) on success
    
    Raises:
        ValueError: If file validation fails
    """
    if not file or file.filename == '':
        raise ValueError("No file selected.")

    if not allowed_file(file.filename):
        raise ValueError("Invalid file type. Please upload a PDF file only.")

    filename = secure_filename(file.filename)
    # Add timestamp to avoid collisions
    import time
    base, ext = os.path.splitext(filename)
    filename = f"{base}_{int(time.time())}{ext}"

    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Validate PDF content
    is_valid, error = validate_pdf(filepath)
    if not is_valid:
        os.remove(filepath)  # Clean up invalid file
        raise ValueError(error)

    return filename, filepath
