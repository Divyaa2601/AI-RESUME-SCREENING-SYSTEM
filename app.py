from flask import Flask, render_template, request, redirect, url_for, session, Response
from parser import extract_text
from extractor import extract_skills, extract_experience
from models import db, User, JobDescription, Resume, MatchResult

from flask_bcrypt import Bcrypt
from datetime import datetime
import csv
import io


# ==========================================
# 🔹 CREATE FLASK APP
# ==========================================
app = Flask(__name__)
app.secret_key = "resume_screening_secret_key"

# ==========================================
# 🔹 DATABASE CONFIGURATION
# ==========================================
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:divya2601@localhost:5432/resume_screening'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)


# ==========================================
# 🔹 SKILL DISPLAY MAPPING
# ==========================================
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


# ==========================================
# 🔹 SIGNUP ROUTE
# ==========================================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "User already exists"

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            username=username,
            password_hash=hashed_pw,
            created_at=datetime.utcnow()
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("signup.html")


# ==========================================
# 🔹 LOGIN ROUTE
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            session["user"] = user.username
            return redirect(url_for("index"))
        else:
            return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==========================================
# 🔹 MAIN APPLICATION
# ==========================================
@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        jd_text = request.form["jd_text"]
        files = request.files.getlist("resumes")

        current_user = User.query.filter_by(username=session["user"]).first()

        # Save JD
        new_jd = JobDescription(
            user_id=current_user.user_id,
            title="Uploaded JD",
            description=jd_text,
            created_at=datetime.utcnow()
        )

        db.session.add(new_jd)
        db.session.commit()

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

            # Save Resume
            new_resume = Resume(
                jd_id=new_jd.jd_id,
                file_name=file.filename,
                extracted_text=text,
                uploaded_at=datetime.utcnow()
            )

            db.session.add(new_resume)
            db.session.commit()

            # Save Match Result
            new_result = MatchResult(
                resume_id=new_resume.resume_id,
                matched_skills=", ".join(prettify(s) for s in matched),
                missing_skills=", ".join(prettify(s) for s in missing),
                score=match_percent,
                experience=extract_experience(text)
            )

            db.session.add(new_result)
            db.session.commit()

            results.append({
                "name": file.filename,
                "score": match_percent / 100,
                "matched_skills": sorted(prettify(s) for s in matched),
                "missing_skills": sorted(prettify(s) for s in missing),
                "exp": extract_experience(text)
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        return render_template("results.html", results=results)

    return render_template("index.html")


# ==========================================
# 🔹 DOWNLOAD CSV (ONLY LATEST SESSION)
# ==========================================
@app.route("/download_csv")
def download_csv():
    if "user" not in session:
        return redirect(url_for("login"))

    current_user = User.query.filter_by(username=session["user"]).first()

    # 🔥 Get latest JD only
    latest_jd = JobDescription.query.filter_by(
        user_id=current_user.user_id
    ).order_by(JobDescription.created_at.desc()).first()

    if not latest_jd:
        return "No results available"

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Resume",
        "Score",
        "Matched Skills",
        "Missing Skills",
        "Experience"
    ])

    resumes = Resume.query.filter_by(jd_id=latest_jd.jd_id).all()

    for resume in resumes:
        result = MatchResult.query.filter_by(resume_id=resume.resume_id).first()

        if result:
            writer.writerow([
                resume.file_name,
                result.score,
                result.matched_skills,
                result.missing_skills,
                result.experience
            ])

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=latest_results.csv"}
    )


# ==========================================
# 🔹 CREATE TABLES
# ==========================================
with app.app_context():
    db.create_all()


# ==========================================
# 🔹 RUN APP
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)