# AI-Based Resume Screening System

An intelligent web application that ranks resumes based on Job Description (JD) skill matching using explainable AI logic.

---

## Project Overview

The AI-Based Resume Screening System helps recruiters evaluate resumes automatically by:

- Extracting text from resumes (PDF)
- Identifying technical skills using NLP
- Comparing resume skills with JD requirements
- Calculating an AI Confidence Score
- Showing matched and missing skills (Explainable AI)

This system eliminates manual screening effort and improves hiring efficiency.

---

## Features

- Upload multiple resumes
- Skill extraction using NLP-based matching
- AI Confidence Score (Skill-based ranking)
- Matched skills detection
- Missing skills detection
- Download results as CSV
- Basic authentication (Login system)
- Explainable resume ranking (No black-box scoring)

---

## Tech Stack

### Backend
- Python
- Flask
- NLP (Regex-based skill extraction)
- CSV (Report generation)

### Frontend
- HTML
- CSS
- JavaScript
- Jinja2 Templates

### Tools
- Git & GitHub
- VS Code
- Postman (API Testing)

---

## System Architecture

```

User → Upload JD + Resumes
↓
Flask Backend
↓
Text Extraction (parser.py)
↓
Skill Extraction (extractor.py)
↓
Skill Matching Logic
↓
AI Confidence Score Calculation
↓
Results Display + CSV Download

```

---

## AI Confidence Score Logic

```

Score = (Number of matched JD skills ÷ Total JD skills) × 100

```

### This ensures:
- Transparent scoring
- No random predictions
- Fully explainable ranking system

---

## Project Structure

```

resume_screening/
│
├── static/
│   ├── styles.css
│   ├── script.js
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── results.html
│
├── app.py
├── extractor.py
├── parser.py
├── matcher.py
├── nlp.py
├── requirements.txt
├── README.md

````

---

## Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Divyaa2601/AI-RESUME-SCREENING-SYSTEM.git
cd AI-RESUME-SCREENING-SYSTEM
````

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run Application

```bash
python app.py
```

Open in browser:

```
http://127.0.0.1:5000
```

---

## Future Improvements

* Replace rule-based matching with Sentence-BERT embeddings
* Add database integration (PostgreSQL / MongoDB)
* Implement JWT-based authentication
* Add Admin dashboard analytics
* Deploy to cloud (Render / AWS / Vercel)
* Implement CI/CD pipeline

---

## Use Cases

* HR Resume Screening
* Campus Placement Automation
* Internship Candidate Filtering
* AI-Based Hiring Systems

---
## 📜 License

This project is developed for academic and research purposes.
