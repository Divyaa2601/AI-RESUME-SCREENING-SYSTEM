from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    Response,
    send_from_directory
)

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

import io
import os

from parser import extract_text
from extractor import extract_skills, extract_experience, format_skills


# =====================================================
# APP CONFIGURATION
# =====================================================

app = Flask(__name__)
app.secret_key = "resume_screening_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = \
    "postgresql://postgres:divya2601@localhost:5432/resume_screening"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =====================================================
# DATABASE MODELS
# =====================================================

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class JobDescription(db.Model):
    jd_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Resume(db.Model):
    resume_id = db.Column(db.Integer, primary_key=True)
    jd_id = db.Column(db.Integer)
    file_name = db.Column(db.String(255))
    extracted_text = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class MatchResult(db.Model):
    result_id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer)
    matched_skills = db.Column(db.Text)
    missing_skills = db.Column(db.Text)
    score = db.Column(db.Float)
    experience = db.Column(db.String(50))


# =====================================================
# FILE VALIDATION
# =====================================================

ALLOWED_EXTENSIONS = {"pdf", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# =====================================================
# USER AUTHENTICATION
# =====================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        user = User(
            username=username,
            password_hash=hashed_pw
        )

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            session["user"] = user.username
            return redirect(url_for("index"))

        return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()
    return redirect(url_for("login"))


# =====================================================
# MAIN APPLICATION PAGE
# =====================================================

@app.route("/", methods=["GET", "POST"])
def index():

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        # Clear old results
        MatchResult.query.delete()
        Resume.query.delete()
        JobDescription.query.delete()
        db.session.commit()

        jd_text = request.form["jd_text"]
        files = request.files.getlist("resumes")

        # Save Job Description
        jd = JobDescription(description=jd_text)
        db.session.add(jd)
        db.session.commit()

        jd_skills = extract_skills(jd_text)

        results = []

        for file in files:

            if allowed_file(file.filename):

                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)

                text = extract_text(file)

                resume_skills = extract_skills(text)

                matched = resume_skills & jd_skills
                missing = jd_skills - resume_skills

                score = (
                    round((len(matched) / len(jd_skills)) * 100, 2)
                    if jd_skills else 0
                )

                # Save Resume
                resume = Resume(
                    jd_id=jd.jd_id,
                    file_name=file.filename,
                    extracted_text=text
                )

                db.session.add(resume)
                db.session.commit()

                exp = extract_experience(text)

                result = MatchResult(
                    resume_id=resume.resume_id,
                    matched_skills=", ".join(matched),
                    missing_skills=", ".join(missing),
                    score=score,
                    experience=exp
                )

                db.session.add(result)
                db.session.commit()

                results.append({
                    "name": file.filename,
                    "score": score,
                    "matched": format_skills(matched),
                    "missing": format_skills(missing),
                    "exp": exp
                })

        # Sort candidates by score
        results.sort(key=lambda x: x["score"], reverse=True)

        return render_template(
            "results.html",
            results=results,
            jd_skills=format_skills(jd_skills)
        )

    return render_template("index.html")


# =====================================================
# EXCEL EXPORT
# =====================================================

@app.route("/download_excel")
def download_excel():

    min_score = request.args.get("min_score", type=float)
    min_exp = request.args.get("min_exp", type=int)

    wb = Workbook()
    ws = wb.active
    ws.title = "Resume Screening Results"

    headers = [
        "Rank",
        "Resume",
        "AI Confidence Score (%)",
        "Matched Skills",
        "Missing Skills",
        "Experience"
    ]

    ws.append(headers)

    results = (
        db.session.query(MatchResult, Resume)
        .join(Resume, MatchResult.resume_id == Resume.resume_id)
        .order_by(MatchResult.score.desc())
        .all()
    )

    rank = 1

    for r, resume in results:

        score = r.score

        exp_years = 0
        if r.experience != "Not Mentioned":
            exp_years = int(r.experience.split()[0])

        # APPLY FILTERS
        if min_score and score < min_score:
            continue

        if min_exp and exp_years < min_exp:
            continue

        ws.append([
            rank,
            resume.file_name,
            f"{score}%",
            r.matched_skills,
            r.missing_skills,
            r.experience
        ])

        rank += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            "attachment;filename=filtered_results.xlsx"
        }
    )
# =====================================================
# RESUME PREVIEW & DOWNLOAD
# =====================================================

@app.route("/resume/<filename>")
def preview_resume(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/download/<filename>")
def download_resume(filename):
    return send_from_directory(
        UPLOAD_FOLDER,
        filename,
        as_attachment=True
    )


# =====================================================
# RUN APPLICATION
# =====================================================

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)