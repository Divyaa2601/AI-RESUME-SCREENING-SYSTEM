from flask import Flask, render_template, request, send_file, redirect, url_for, session
from parser import extract_text
from extractor import extract_skills, extract_experience
import csv

app = Flask(__name__)
app.secret_key = "resume_screening_secret_key"

# ---------- Skill Display Names ----------

DISPLAY_NAMES = {
    "aws": "AWS",
    "ci/cd": "CI/CD",
    "github actions": "GitHub Actions",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "linux": "Linux",
    "python": "Python",
    "flask": "Flask",
    "django": "Django",
    "fastapi": "FastAPI",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "rest api": "REST API",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "postman": "Postman",
    "swagger": "Swagger",
    "cnn": "CNN",
    "transformer": "Transformer"
}

def prettify(skill):
    return DISPLAY_NAMES.get(skill, skill.upper())


# ---------- Simple Login ----------

USERS = {"admin": "admin123"}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if USERS.get(request.form["username"]) == request.form["password"]:
            session["user"] = request.form["username"]
            return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Main App ----------

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        jd_text = request.form["jd_text"]
        files = request.files.getlist("resumes")

        # Extract JD skills ONCE
        jd_skills = extract_skills(jd_text)

        results = []

        for file in files:
            text = extract_text(file)
            resume_skills = extract_skills(text)

            matched = resume_skills & jd_skills
            missing = jd_skills - resume_skills

            match_percent = round(
                (len(matched) / len(jd_skills)) * 100, 2
            ) if jd_skills else 0

            results.append({
                "name": file.filename,
                "score": match_percent / 100,

                # ✅ USE prettify() properly
                "matched_skills": sorted(prettify(s) for s in matched),
                "missing_skills": sorted(prettify(s) for s in missing),

                "exp": extract_experience(text)
            })

        # Sort by match %
        results.sort(key=lambda x: x["score"], reverse=True)

        # ---------- Save CSV ----------
        with open("results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Rank",
                "Resume",
                "Match %",
                "Matched Skills",
                "Missing Skills",
                "Experience"
            ])

            for i, r in enumerate(results, start=1):
                writer.writerow([
                    i,
                    r["name"],
                    round(r["score"] * 100, 2),
                    ", ".join(r["matched_skills"]),
                    ", ".join(r["missing_skills"]),
                    r["exp"]
                ])

        return render_template("results.html", results=results)

    return render_template("index.html")

@app.route("/download_csv")
def download_csv():
    return send_file("results.csv", as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
