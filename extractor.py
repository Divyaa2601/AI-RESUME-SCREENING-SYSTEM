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

    # CI/CD
    "ci cd": "ci/cd",
    "ci/cd": "ci/cd",
    "github actions": "ci/cd",

    # Deep Learning
    "cnn": "deep learning",
    "cnns": "deep learning",
    "transformer": "deep learning",
    "transformers": "deep learning",
    "deep learning": "deep learning",

    # Machine Learning
    "machine learning": "machine learning",

    # NLP
    "nlp": "nlp",

    # AWS
    "aws": "aws",
    "lambda": "aws",
    "api gateway": "aws",
    "dynamodb": "aws",
    "s3": "aws",
    "ec2": "aws",

    # DevOps
    "docker": "docker",
    "kubernetes": "kubernetes",

    # Frameworks
    "flask": "flask",
    "django": "django",
    "fastapi": "fastapi",

    # Programming
    "python": "python",

    # Databases
    "mysql": "mysql",
    "postgresql": "postgresql",

    # Version Control
    "git": "git",
    "github": "git"
}


# ---------- Skill Display Names ----------
# Converts canonical names into professional display names

DISPLAY_SKILLS = {
    "aws": "AWS",
    "nlp": "NLP",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "ci/cd": "CI/CD",
    "git": "Git",
    "docker": "Docker",
    "flask": "Flask",
    "django": "Django",
    "fastapi": "FastAPI",
    "python": "Python",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "kubernetes": "Kubernetes"
}


# ---------- Extract Skills From Any Text ----------

def extract_skills(text: str):
    text = normalize(text)
    found = set()

    for variant, canonical in SKILL_MAP.items():
        if variant in text:
            found.add(canonical)

    return found


# ---------- Format Skills For UI ----------

def format_skills(skill_set):
    formatted = []

    for skill in skill_set:
        formatted.append(DISPLAY_SKILLS.get(skill, skill.title()))

    return formatted


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