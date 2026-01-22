# App Reviewer AI 📱🤖

App Reviewer AI is a comprehensive platform designed to scrape, analyze, and visualize app store reviews using advanced AI pipelines. It helps app developers and product managers turn user feedback into actionable insights.

## 🚀 Quick Start (Unified Command)

Run everything with a single command from the project root:
```bash
./run.sh
```
This will start the backend as a background process and the frontend as a foreground process.

## 🛠️ Getting Started

### Prerequisites
- Python 3.9+
- OpenAI API Key

### Configuration
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Configure environment:
   - Copy `.env.example` to `.env`.
   - Add your `OPENAI_API_KEY`.
5. Start the server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Start a simple HTTP server:
   ```bash
   python -m http.server 3000
   ```
3. Open http://localhost:3000 in your browser.

## 📂 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes and schemas
│   │   ├── core/         # Job management and background worker
│   │   ├── pipelines/    # AI analysis logic (Sentiment, Issues, Features, etc.)
│   │   ├── services/     # Review fetcher and PDF generator
│   │   └── config.py     # Environment settings
│   ├── data/             # Locally saved JSON review exports
│   └── main.py           # Application entry point
├── frontend/
│   ├── index.html        # Main dashboard structure
│   ├── styles.css        # Modern glassmorphism styling
│   └── app.js            # Frontend logic and API interaction
└── app_reviewer_api.txt  # Project-specific configuration reference
```

## 📝 License
This project is built for professional app review analysis. Enjoy!
