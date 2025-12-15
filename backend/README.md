# Backend - AI Feedback System

This backend contains:
- **Task 1**: Rating Prediction via Prompting (Jupyter Notebook)
- **Task 2**: FastAPI Backend for AI Feedback System

## Task 1 - Rating Prediction

**File**: `final.ipynb`

9 different prompting approaches to classify Yelp reviews into 1-5 star ratings.

### To Run Task 1:
```bash
jupyter notebook final.ipynb
```

## Task 2 - FastAPI Backend

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Gemini API key (optional, defaults to hardcoded key):
```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or set it in `main.py` directly.

3. Run the server:
```bash
python main.py
```

Or using uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

- `GET /` - Health check
- `POST /api/submit-review` - Submit a new review
- `GET /api/submissions` - Get all submissions (admin)
- `GET /api/stats` - Get statistics (admin)

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Data Storage

Submissions are stored in `submissions.json` file.
