# Fynd AI Intern - Take Home Assessment

Complete solution for the Fynd AI Intern assessment with Task 1 (Rating Prediction) and Task 2 (AI Feedback System).

## 📁 Repository Structure

```
Fynd Assignment/
├── backend/              # Backend (Task 1 + Task 2)
│   ├── final.ipynb      # Task 1: Rating Prediction Notebook
│   ├── main.py          # Task 2: FastAPI Backend
│   ├── Data/            # Yelp Reviews Dataset
│   ├── *.csv            # Task 1 Results
│   └── requirements.txt
│
├── user/                 # User Dashboard
└── admin/                # Admin Dashboard
```

## 🚀 Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Backend runs at: `http://localhost:8000`

### User Frontend

```bash
cd user
npm install
npm run dev
```

User frontend runs at: `http://localhost:3000`

### Admin Frontend

```bash
cd admin
npm install
npm run dev
```

Admin frontend runs at: `http://localhost:3001`

## 🔧 Environment Setup

Create a `.env` file in the repository root (same folder as `docker-compose.yml`).

You can copy from `.env.example`:

```bash
cp .env.example .env
```

Required variables:
- `GEMINI_API_KEY` (optional for local testing; required for real AI responses)

## 📋 Task 1: Rating Prediction via Prompting

**Location**: `backend/final.ipynb`

- ✅ 9 different prompting approaches
- ✅ Evaluation on 200 sample reviews
- ✅ Metrics: Accuracy, JSON Validity, Consistency
- ✅ Comparison table with all approaches

### Approaches Implemented:
1. Direct Prompting
2. Chain-of-Thought Reasoning
3. Template-Based with Few-Shot Examples
4. Output Validation
5. Criteria-Based Rating
6. Self-Consistency
7. Polarity Mapping
8. Rule-Based
9. Token Attention

### To Run:
```bash
cd backend
jupyter notebook final.ipynb
```

## 🎯 Task 2: Two-Dashboard AI Feedback System

### User Dashboard (`/`)
- Submit reviews with star ratings (1-5)
- Receive AI-generated responses
- Clean, modern UI

### Admin Dashboard (`/admin`)
- View all submitted reviews
- Real-time analytics (total reviews, average rating, distribution)
- AI-generated summaries
- AI-suggested recommended actions
- Auto-refreshes every 5 seconds

### Features:
- ✅ Web-based (React + FastAPI)
- ✅ AI integration (Gemini API)
- ✅ Data persistence (JSON file)
- ✅ Real-time updates
- ✅ Modern UI with Tailwind CSS

## 🌐 Deployment

### Backend (Render/Railway/Railway)
1. Push to GitHub
2. Connect repository
3. Set `GEMINI_API_KEY` environment variable
4. Deploy with: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Frontend (Vercel/Netlify)
1. Push to GitHub
2. Connect repository
3. Set `VITE_API_URL` environment variable (your backend URL)
4. Build command: `npm run build`
5. Output directory: `dist`

### Docker (Recommended for easy deployment)

This repository includes:
- `backend/Dockerfile`
- `user/Dockerfile` + `user/nginx.conf` (serves SPA + proxies `/api/*` to backend)
- `admin/Dockerfile` + `admin/nginx.conf` (serves SPA + proxies `/api/*` to backend)
- `docker-compose.yml`

Steps:

```bash
# from repo root
cp .env.example .env

# add GEMINI_API_KEY inside .env
docker compose up --build
```

URLs:
- User Frontend: `http://localhost:3001`
- Admin Frontend: `http://localhost:3002`
- Backend: `http://localhost:8000`

Notes:
- In Docker mode, the frontend proxies API calls to the backend automatically via Nginx.
- In local dev mode (`npm run dev`), Vite proxies `/api` to `http://localhost:8000` (see `user/vite.config.js` and `admin/vite.config.js`).

## 🔑 API Key

The Gemini API key is configured in:
- Task 1: `backend/final.ipynb` (Cell 3)
- Task 2: `backend/main.py` (line 24)

Or set environment variable: `GEMINI_API_KEY`

## 📊 Deliverables

- ✅ GitHub Repository
- ✅ Python notebook for Task 1
- ✅ Application code for Task 2
- ✅ Supporting files
- 📝 Report (to be created)
- 🌐 Deployment links (to be deployed)

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, Google Gemini API
- **Frontend**: React, Vite, Tailwind CSS, Axios
- **Task 1**: Jupyter Notebook, pandas, numpy

## 📝 Requirements

- Python 3.8+
- Node.js 16+
- npm or yarn
