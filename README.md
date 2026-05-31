# InterviewAI 🤖 – Resume-Based AI Interview Preparation Platform

> **Built with Flask + Google Gemini AI** · Full-stack interview simulator that generates personalized questions from your resume and evaluates answers in real-time.

---

## 🚀 Features

| Feature | Description |
|---|---|
| 📄 Resume Upload | Upload PDF resume — AI extracts skills, projects, certs |
| 🧠 AI Analysis | Gemini reads resume and determines your level (Fresher/Intermediate/Advanced) |
| 🎯 Personalized Questions | 12 questions: 40% Technical, 30% Project, 30% HR — all resume-specific |
| ⚡ Follow-up Questions | Dynamic follow-ups based on what you mention |
| 🎙️ Voice Mode | Answer by speaking using Web Speech API |
| ⏱️ Interview Timer | 2-minute countdown per question |
| 📊 Detailed Reports | Radar chart, bar chart, score breakdown, strengths, weaknesses |
| 📚 Recommendations | Topic-based learning suggestions for weak areas |
| 🗂️ History Tracking | All sessions stored in SQLite with full Q&A review |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11 + Flask
- **AI**: Google Gemini 1.5 Flash (`google-generativeai`)
- **PDF Parsing**: PyPDF2
- **Database**: SQLite
- **Frontend**: HTML5 + CSS3 + Vanilla JavaScript
- **Voice**: Web Speech API
- **Charts**: HTML5 Canvas (no external library)
- **Deployment**: Render (gunicorn) and Vercel (serverless Flask adapter)

---

## 📁 Project Structure

```
InterviewAI/
├── app.py                    # Flask application & routes
├── api/index.py              # Vercel entry point
├── render.yaml               # Render deployment config
├── vercel.json               # Vercel routing config
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (never commit!)
├── database.db               # SQLite database (auto-created)
├── templates/
│   ├── index.html            # Landing + resume upload
│   ├── dashboard.html        # Stats overview
│   ├── interview.html        # Live interview page
│   ├── result.html           # Final report
│   └── history.html          # Past sessions
├── static/
│   ├── css/style.css         # Dark-mode glassmorphism UI
│   └── js/script.js          # Frontend logic
├── uploads/                  # Temp PDF storage
└── utils/
    ├── database.py           # SQLite CRUD operations
    ├── pdf_parser.py         # PDF text extraction
    ├── question_generator.py # Gemini question generation
    └── evaluator.py          # Gemini answer evaluation
```

---

## ⚙️ Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/InterviewAI.git
cd InterviewAI
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Edit `.env` and add your Gemini API key:
```env
GEMINI_API_KEY=your_key_from_aistudio.google.com
SECRET_KEY=your_random_flask_secret
```

Get your free Gemini API key at: https://aistudio.google.com/

### 5. Run the Application
```bash
python app.py
```
Open http://localhost:5000 in your browser.

---

## 🚀 Deployment on Render

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit: InterviewAI"
git branch -M main
git remote add origin https://github.com/yourusername/InterviewAI.git
git push -u origin main
```

**⚠️ Important**: Keep `.env` out of Git and set secrets in the host dashboard.

### 2. Deploy on Render
1. Go to [render.com](https://render.com) and sign up
2. Click **New → Web Service**
3. Connect your GitHub repository
4. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Add Environment Variables:
   - `GEMINI_API_KEY` = your key
   - `SECRET_KEY` = random string
6. Click **Deploy**

Render is the better choice if you want SQLite session history to persist for the lifetime of the service.

---

## 🌐 Deployment on Vercel

Vercel can run the app through `api/index.py`, but its filesystem is ephemeral. Uploaded PDFs and SQLite data are temporary there, so use Render if you need persistent interview history.

### 1. Push the same GitHub repo
Make sure `api/index.py` and `vercel.json` are committed.

### 2. Import the repo into Vercel
1. Go to [vercel.com](https://vercel.com) and import the GitHub repository
2. Keep the default Python settings
3. Add Environment Variables:
   - `GEMINI_API_KEY` = your key
   - `SECRET_KEY` = random string
4. Deploy

---

## 🔒 Security Notes

- `.env` is **never committed** to Git
- Uploaded PDFs are stored temporarily in `/uploads/`
- File validation prevents non-PDF uploads
- Maximum upload size: 16MB
- Flask session uses a secret key for security
- On Vercel, uploaded PDFs and SQLite data live in temporary storage only

## OCR Support (scanned/image PDFs)

This project now attempts OCR when PyPDF2 can't extract text (useful for scanned resumes). OCR uses `pymupdf` (PyMuPDF) to render pages and `pytesseract` to extract text.

System dependency: install Tesseract OCR on the host machine.

- Ubuntu / Debian (example):

```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr libtesseract-dev
```

- Windows: download and install from https://github.com/tesseract-ocr/tesseract

On Render you may need to add a build step or custom Docker image that includes Tesseract. If you don't want to install Tesseract on the host, instruct users to upload text-based PDFs instead.

---

## 📊 LinkedIn Post Idea

> 🚀 Excited to share **InterviewAI** – an AI-powered resume-based interview preparation platform I built using:
> 
> ✅ Flask (Python backend)
> ✅ Google Gemini AI (LLM)
> ✅ PyPDF2 (resume parsing)
> ✅ SQLite (session tracking)
> ✅ Web Speech API (voice mode)
> 
> Upload your resume → get 12 personalized interview questions → get AI evaluation for every answer → download detailed report 🎯
> 
> #Python #Flask #GenerativeAI #NLP #WebDevelopment #GeminiAI

---

## 📄 License

MIT License – Feel free to use and modify for personal/commercial use.
