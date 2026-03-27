from flask import (
    Flask, render_template, request, redirect,
    url_for, session, Response, send_from_directory
)

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from openpyxl import Workbook

import io
import os

from parser import extract_text
from extractor import extract_skills, extract_experience, format_skills
from PIL import Image

from dotenv import load_dotenv
load_dotenv()
if not os.getenv("GOOGLE_CLIENT_ID"):
    print("❌ GOOGLE_CLIENT_ID not loaded")
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
# =====================================================
# APP CONFIGURATION
# =====================================================

app = Flask(__name__)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # only for local

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)
app.secret_key = "resume_screening_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///database.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

UPLOAD_FOLDER = "uploads"
PROFILE_FOLDER = "static/profile_pics"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_FOLDER, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# =====================================================
# DATABASE MODELS
# =====================================================

class User(db.Model):
    __tablename__ = "user"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(200), default="default.png")  # ✅ FIX
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
# HELPERS
# =====================================================

ALLOWED_EXTENSIONS = {"pdf", "docx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None


# =====================================================
# AUTHENTICATION
# =====================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        user = User(username=username, password_hash=hashed_pw)

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            session["user_id"] = user.user_id
            session["username"] = user.username
            return redirect("/")

        return "Invalid credentials"

    return render_template("login.html")

@app.route("/login/google")
def google_login():
    return google.authorize_redirect(
            redirect_uri="https://ai-resume-screening-system-n5p3.onrender.com/login/google/callback"
        )

@app.route("/login/google/callback")
def google_callback():

    token = google.authorize_access_token()

    user_info = google.get(
        'https://openidconnect.googleapis.com/v1/userinfo'
    ).json()

    email = user_info['email']

    username = email.split("@")[0]
    user = User.query.filter_by(username=email).first()
    if not user:
        user = User(
            username=email,
            password_hash=bcrypt.generate_password_hash("google_login").decode("utf-8")
        )
        db.session.add(user)
        db.session.commit()

    session["user_id"] = user.user_id
    session["username"] = user.username

    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =====================================================
# MAIN PAGE
# =====================================================

@app.route("/", methods=["GET", "POST"])
def index():

    if "user_id" not in session:
        return redirect("/login")

    user = get_current_user()

    if request.method == "POST":

        # Clear previous session data
        MatchResult.query.delete()
        Resume.query.delete()
        JobDescription.query.delete()
        db.session.commit()

        jd_text = request.form["jd_text"]
        files = request.files.getlist("resumes")

        jd = JobDescription(
            description=jd_text,
            user_id=session["user_id"]
        )

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
        min_score = float(request.args.get("min_score", 0) or 0)
        min_exp = float(request.args.get("min_exp", 0) or 0)
        sort_by = request.args.get("sort", "score")

        filtered_results = []

        for r in results:

            exp_val = 0
            if "year" in str(r["exp"]).lower():
                try:
                    exp_val = float(r["exp"].split()[0])
                except:
                    exp_val = 0

            if r["score"] >= min_score and exp_val >= min_exp:
                filtered_results.append(r)

        # SORTING
        if sort_by == "score":
            filtered_results.sort(key=lambda x: x["score"], reverse=True)

        return render_template(
            "results.html",
            results=filtered_results,
            jd_skills=format_skills(jd_skills),
            user=user  # ✅ important for navbar image
        )

    return render_template("index.html", user=user)


# =====================================================
# PROFILE PAGE
# =====================================================

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    user = get_current_user()

    total_resumes = Resume.query.count()
    scores = [r.score for r in MatchResult.query.all()]

    avg_score = round(sum(scores)/len(scores), 2) if scores else 0
    best_score = max(scores) if scores else 0

    return render_template(
        "profile.html",
        user=user,
        total_resumes=total_resumes,
        avg_score=avg_score,
        best_score=best_score
    )


# =====================================================
# EDIT PROFILE
# =====================================================

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect("/login")

    user = get_current_user()

    if request.method == "POST":

        new_username = request.form.get("username")
        new_password = request.form.get("password")
        file = request.files.get("profile_image")
        remove_image = request.form.get("remove_image")

        if new_username:
            user.username = new_username
            session["username"] = new_username

        if new_password:
            user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")

        # 🔥 REMOVE FIRST (priority)
        if remove_image == "yes":

            if user.profile_image != "default.png":
                old_path = os.path.join(PROFILE_FOLDER, user.profile_image)
                if os.path.exists(old_path):
                    os.remove(old_path)

            user.profile_image = "default.png"

        # 🔥 ELSE upload image
        elif file and file.filename and allowed_image(file.filename):

            filename = f"user_{user.user_id}.png"
            filepath = os.path.join(PROFILE_FOLDER, filename)

            img = Image.open(file)
            img = img.resize((200, 200))
            img.save(filepath)

            user.profile_image = filename
        db.session.commit()

        return redirect("/profile")

    return render_template("edit_profile.html", user=user)


# =====================================================
# EXCEL EXPORT
# =====================================================

@app.route("/download_excel", methods=["GET", "POST"])
def download_excel():

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"

    ws.append([
        "Rank", "Resume", "Score",
        "Matched Skills", "Missing Skills", "Experience"
    ])

    # 🔥 CASE 1: FILTERED DATA (POST)
    if request.method == "POST":

        data = request.get_json()

        if not data:
            return "No data", 400

        rank = 1
        for row in data:
            ws.append([
                rank,
                row.get("name", ""),
                row.get("score", ""),
                row.get("skills", ""),
                "",   # missing not needed here
                row.get("exp", "")
            ])
            rank += 1

    # 🔥 CASE 2: ALL DATA (GET)
    else:

        results = (
            db.session.query(MatchResult, Resume)
            .join(Resume, MatchResult.resume_id == Resume.resume_id)
            .order_by(MatchResult.score.desc())
            .all()
        )

        rank = 1
        for r, resume in results:
            ws.append([
                rank,
                resume.file_name,
                f"{r.score}%",
                r.matched_skills,
                r.missing_skills,
                r.experience
            ])
            rank += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = "filtered.xlsx" if request.method == "POST" else "all_results.xlsx"

    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

@app.route("/download_top5", methods=["POST"])
def download_top5():

    data = request.get_json()

    wb = Workbook()
    ws = wb.active

    ws.append(["Rank", "Resume", "Score", "Skills", "Experience"])

    for i,row in enumerate(data, start=1):
        ws.append([
            i, 
            row["name"],
            row["score"],
            row["skills"],
            row["exp"]
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
    output.getvalue(),  
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    headers={
        "Content-Disposition": "attachment; filename=filtered.xlsx"
    }
)
# =====================================================
# FILE ROUTES
# =====================================================

@app.route("/resume/<filename>")
def preview_resume(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/download/<filename>")
def download_resume(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# =====================================================
# DELETE ACCOUNT
# =====================================================

@app.route("/delete_account", methods=["POST"])
def delete_account():

    if "user_id" not in session:
        return redirect("/login")

    user = get_current_user()

    # Delete user from database
    db.session.delete(user)
    db.session.commit()

    # Clear session
    session.clear()

    return redirect("/signup")

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    import os
    port = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=port)