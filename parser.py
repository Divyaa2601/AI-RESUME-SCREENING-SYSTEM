import PyPDF2
import docx2txt


def extract_text(file):
    """
    Extract text from uploaded PDF or DOCX file
    """
    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    elif filename.endswith(".docx"):
        return docx2txt.process(file)

    else:
        return ""
