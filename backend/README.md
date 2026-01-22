# App Reviewer AI - Backend

Automated App Store Review Intelligence Platform - Backend API

## Quick Start

### Prerequisites
- Python 3.10+
- Redis (optional, falls back to in-memory)
- OpenAI API key

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Running the Server

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Create analysis job |
| `/status/{id}` | GET | Get job status |
| `/result/{id}` | GET | Get completed result |
| `/export/pdf/{id}` | GET | Download PDF report |
| `/health` | GET | Health check |

## Usage Example

```bash
# Submit analysis
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"app_url": "https://apps.apple.com/us/app/example/id123456789", "platform": "ios"}'

# Response: {"analysis_id": "uuid", "status": "created", "estimated_time_sec": 60}

# Check status
curl http://localhost:8000/status/{analysis_id}

# Get result (when completed)
curl http://localhost:8000/result/{analysis_id}

# Download PDF
curl -O http://localhost:8000/export/pdf/{analysis_id}
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration
│   ├── api/
│   │   ├── routes.py        # API endpoints
│   │   └── schemas.py       # Pydantic models
│   ├── core/
│   │   ├── cache.py         # Redis/in-memory cache
│   │   ├── job_manager.py   # Job lifecycle
│   │   └── worker.py        # Background processing
│   ├── adapters/
│   │   ├── base.py          # Adapter interface
│   │   ├── appstore.py      # iOS App Store
│   │   └── playstore.py     # Google Play
│   ├── pipelines/
│   │   ├── base.py          # Base pipeline
│   │   ├── sentiment.py     # Sentiment analysis
│   │   ├── issues.py        # Issue extraction
│   │   ├── features.py      # Feature detection
│   │   ├── monetization.py  # Monetization risks
│   │   └── actions.py       # Action recommendations
│   ├── aggregation/
│   │   └── aggregator.py    # Result aggregation
│   └── services/
│       ├── review_fetcher.py
│       └── pdf_generator.py
├── tests/
├── requirements.txt
└── .env.example
```

## Job Lifecycle

```
CREATED → FETCHING_REVIEWS → ANALYZING_REVIEWS → AGGREGATING_RESULTS → COMPLETED | FAILED
```

## Configuration

See `.env.example` for all configuration options:
- `OPENAI_API_KEY` - Required
- `REDIS_URL` - Optional (defaults to in-memory)
- `MAX_TOKEN_BUDGET_PER_JOB` - Cost control
- `MAX_REVIEW_COUNT` - Review limit
