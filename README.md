# App Reviewer AI 📱🤖

App Reviewer AI is a comprehensive platform designed to scrape, analyze, and visualize app store reviews using advanced AI pipelines. It helps app developers and product managers turn user feedback into actionable insights.

## 🚀 Key Features

- **Multi-Region Scraping**: Support for 11+ App Store regions (US, UK, Turkey, Germany, France, etc.) with automatic URL localization.
- **Advanced AI Analysis**: 5 parallel AI pipelines powered by GPT-4o-mini:
  - **Sentiment & Emotion**: Categorizes reviews into Positive, Neutral, and Negative sentiments with emoji distribution.
  - **Bug Extraction**: Identifies technical issues and crashes.
  - **Feature Requests**: Surfaces what users are asking for.
  - **Monetization Analysis**: Detects friction in payment flows and subscription models.
  - **Actionable Recommendations**: Maps findings to specific PRD-ready tasks with priority levels.
- **Interactive Dashboard**:
  - **Rating Distribution Chart**: Visual bar charts showing star ratings.
  - **Review Filtering**: Filter reviews by star count (1-5).
  - **JSON Export**: Download raw scraped data for external use.
- **Professional Reporting**: Export analysis results to a styled PDF report.

## 🏗️ Technical Architecture

### Backend (Python/FastAPI)
- **Async Job Management**: Handles long-running AI tasks using background workers.
- **Intelligent Caching**: In-memory caching for faster subsequent lookups.
- **Modular Pipelines**: Extensible architecture for adding new AI analysis metrics.
- **RSS Parser**: High-performance scraping of App Store review feeds.

### Frontend (Vanilla JS/CSS)
- **Modern Dark UI**: Sleek, glassmorphism design with responsive layout.
- **Dynamic URL Handling**: Automatically updates App Store URLs based on the selected region.
- **Smooth UX**: Loading states, progress bars, and smooth scrolling to analysis sections.

## 🛠️ Getting Started

### Prerequisites
- Python 3.9+
- OpenAI API Key

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment:
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
