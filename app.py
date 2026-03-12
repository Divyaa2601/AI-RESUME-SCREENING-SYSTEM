from flask import Flask, render_template, request, redirect, url_for, session, Response
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from extractor import format_skills
import csv
import io

from parser import extract_text
from extractor import extract_skills, extract_experience

app = Flask(__name__)
app.secret_key = "resume_screening_secret_key"

# -----------------------------
# DATABASE CONFIGURATION
# -----------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:divya2601@localhost:5432/resume_screening'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# -----------------------------
# DATABASE MODELS
# -----------------------------

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


# -----------------------------
# FILE VALIDATION
# -----------------------------

ALLOWED_EXTENSIONS = {"pdf", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# -----------------------------
# SIGNUP
# -----------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        user = User(username=username, password_hash=hashed_pw)

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("signup.html")


# -----------------------------
# LOGIN
# -----------------------------

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


# -----------------------------
# LOGOUT
# -----------------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------------
# MAIN PAGE
# -----------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Clear previous screening results
        MatchResult.query.delete()
        Resume.query.delete()
        JobDescription.query.delete()
        db.session.commit()

        jd_text = request.form["jd_text"]
        files = request.files.getlist("resumes")

        jd = JobDescription(description=jd_text)
        db.session.add(jd)
        db.session.commit()

        jd_skills = extract_skills(jd_text)

        results = []

        for file in files:

            if allowed_file(file.filename):

                text = extract_text(file)
                resume_skills = extract_skills(text)

                matched = resume_skills & jd_skills
                missing = jd_skills - resume_skills

                score = round((len(matched) / len(jd_skills)) * 100, 2) if jd_skills else 0

                resume = Resume(
                    jd_id=jd.jd_id,
                    file_name=file.filename,
                    extracted_text=text
                )

                db.session.add(resume)
                db.session.commit()

                result = MatchResult(
                    resume_id=resume.resume_id,
                    matched_skills=", ".join(matched),
                    missing_skills=", ".join(missing),
                    score=score,
                    experience=extract_experience(text)
                )

                db.session.add(result)
                db.session.commit()

                results.append({
                    "name": file.filename,
                    "score": score,
                    "matched": format_skills(matched),
                    "missing": format_skills(missing),
                    "exp": extract_experience(text)
                })

        results.sort(key=lambda x: x["score"], reverse=True)

        return render_template("results.html", results=results)

    return render_template("index.html")


# -----------------------------
# CSV DOWNLOAD
# -----------------------------

@app.route("/download_csv")
def download_csv():

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Rank","Resume", "Score", "Matched Skills", "Missing Skills", "Experience"])

    results = db.session.query(MatchResult, Resume)\
        .join(Resume, MatchResult.resume_id == Resume.resume_id)\
        .order_by(MatchResult.score.desc())\
        .all()
    
    rank = 1

    for r, resume in results:
        writer.writerow([
            rank,
            resume.file_name,
            f"{r.score}%",
            r.matched_skills,
            r.missing_skills,
            r.experience
        ])

        rank+=1

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=results.csv"}
    )

# -----------------------------
# RUN APP
# -----------------------------

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)