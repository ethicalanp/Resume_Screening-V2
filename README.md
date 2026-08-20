# Resume Screener V2

Resume Screener is a full-stack application for evaluating resumes against job descriptions. It combines resume parsing, semantic similarity, keyword matching, and rule-based signals into an ATS score, then provides candidate-facing feedback or an HR-facing screening summary.

The project includes a React frontend, a FastAPI backend, and a SQLite database.

## Features

- **Candidate ATS Check:** Upload a PDF, DOC, or DOCX resume and compare it with a job description.
- **Transparent scoring:** View the overall ATS score, semantic score, keyword score, matched keywords, and missing keywords.
- **AI feedback:** Generate structured improvement feedback for candidates and concise summaries for hiring teams.
- **HR portal:** Create job postings, screen resumes against saved roles, review screening results, and record decisions.
- **Persistent results:** Store candidate checks, jobs, and screenings with SQLAlchemy.
- **Local fallback:** The application remains usable without a Gemini API key by using fallback embeddings and feedback.

## Technology Stack

- **Frontend:** React 18, Vite, Axios
- **Backend:** Python, FastAPI, Uvicorn, Pydantic
- **Resume parsing:** `pdfminer.six` and `python-docx`
- **Scoring:** scikit-learn and custom keyword, experience, education, and format signals
- **AI services:** Google Gemini embeddings and text generation
- **Persistence:** SQLAlchemy with SQLite by default

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer and npm
- A Google Gemini API key is optional

### 1. Install backend dependencies

From the repository root:

```bash
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Install the Python packages:

```bash
python -m pip install -r requirements.txt
```

### 2. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 3. Configure environment variables

Create a `.env` file in the repository root when using Gemini or a non-default database:

```env
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=sqlite:///./resume_screener.db
```

`GEMINI_API_KEY` may be omitted. Without it, the backend uses local fallback behavior. Do not commit `.env` or API keys.

### 4. Run the application

Start the backend in one terminal:

```bash
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Vite proxies `/api` requests to the backend at port `8000`.

For a convenience launcher, run `python app.py` from the repository root. It starts both services and selects available ports; the separate commands above are recommended when developing against Vite's configured proxy.

## How It Works

### Candidate workflow

1. Upload a resume in PDF, DOC, or DOCX format.
2. Paste a job description of at least 50 characters.
3. Review the ATS, semantic, and keyword scores, along with matched and missing keywords.
4. Use the structured feedback to improve the resume for the selected role.

### HR workflow

1. Create a job with a title, company, and job description.
2. Upload a resume for that job.
3. Review the ATS scores, keyword gaps, AI summary, and detailed feedback.
4. Track the candidate decision as `pending`, `shortlist`, `reject`, or `hold` through the API.

Uploaded resumes must be no larger than 10 MB and contain enough extractable text to be screened.

## Previous Experimentation

The earlier notebook-based work is preserved in the **Old Prototype Experimentation** repository:

[Old Prototype Experimentation](https://github.com/ethicalanp/Resume_Screening_Prototype-NLP-project)

That repository provides historical context for the NLP experiments that informed this application.

## License

No license has been specified for this repository yet.
