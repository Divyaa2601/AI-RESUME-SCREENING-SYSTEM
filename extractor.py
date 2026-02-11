import re

# ---------- Normalization ----------

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9+/ ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ---------- Canonical Skill Dictionary ----------

# All variants map to ONE canonical name
SKILL_MAP = {
    "ci cd": "ci/cd",
    "ci/cd": "ci/cd",
    "github actions": "ci/cd",

    "cnn": "deep learning",
    "cnns": "deep learning",
    "transformer": "deep learning",
    "transformers": "deep learning",
    "deep learning": "deep learning",

    "machine learning": "machine learning",
    "nlp": "nlp",

    "aws": "aws",
    "lambda": "aws",
    "api gateway": "aws",
    "dynamodb": "aws",
    "s3": "aws",
    "ec2": "aws",

    "docker": "docker",
    "kubernetes": "kubernetes",

    "flask": "flask",
    "django": "django",
    "fastapi": "fastapi",

    "python": "python",
    "mysql": "mysql",
    "postgresql": "postgresql",

    "git": "git",
    "github": "git"
}


# ---------- Extract Skills From Any Text ----------

def extract_skills(text: str):
    text = normalize(text)
    found = set()

    for variant, canonical in SKILL_MAP.items():
        if variant in text:
            found.add(canonical)

    return found


# ---------- Experience Extraction ----------

def extract_experience(resume_text: str):
    resume_text = resume_text.lower()

    patterns = [
        r'(\d+)\+?\s+years?\s+of\s+experience',
        r'(\d+)\+?\s+years?\s+experience',
        r'experience\s+of\s+(\d+)\+?\s+years?'
    ]

    for pattern in patterns:
        match = re.search(pattern, resume_text)
        if match:
            return f"{match.group(1)} years"

    return "Not Mentioned"
