import PyPDF2
import docx2txt

def extract_text(file):
    """
    Extract text from uploaded PDF or DOCX file
    """

    filename = file.filename.lower()

    # -------- PDF --------
    if filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        text = ""

        for page in reader.pages:
            text += page.extract_text() or ""

        return text

    # -------- DOCX --------
    elif filename.endswith(".docx"):
        text = docx2txt.process(file)
        return text

    # -------- Unsupported file --------
    else:
        return ""