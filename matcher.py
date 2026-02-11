from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def rank_resumes(jd_text, resume_data):
    results = []

    # Normalize JD skills (already extracted earlier)
    jd_skills = set()

    for r in resume_data:
        # We assume extractor already used JD text
        jd_skills.update(r.get("matched_skills", []))
        jd_skills.update(r.get("missing_skills", []))

    jd_skill_count = len(jd_skills) if jd_skills else 1  # avoid division by zero

    for r in resume_data:
        matched = set(r.get("matched_skills", []))
        missing = set(r.get("missing_skills", []))

        # 🔥 SKILL-BASED SCORE
        score = len(matched) / jd_skill_count

        results.append({
            "name": r["name"],
            "score": score,                  # NOW skill-based
            "skills": r["skills"],
            "matched_skills": list(matched),
            "missing_skills": list(missing),
            "exp": r["exp"]
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    return results
