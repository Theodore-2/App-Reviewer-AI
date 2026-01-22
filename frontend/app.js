/**
 * App Reviewer AI - Frontend JavaScript
 */

const API_BASE = 'http://localhost:8000';

// State
let currentReviews = [];
let currentAppName = '';
let currentAnalysisId = null;

// DOM Elements
const appUrlInput = document.getElementById('appUrl');
const localeSelect = document.getElementById('locale');
const limitSelect = document.getElementById('limit');
const fetchBtn = document.getElementById('fetchBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const downloadBtn = document.getElementById('downloadBtn');
const loadingDiv = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const closeErrorBtn = document.getElementById('closeError');
const resultsSection = document.getElementById('results');
const reviewsGrid = document.getElementById('reviewsGrid');
const appNameEl = document.getElementById('appName');
const reviewCountEl = document.getElementById('reviewCount');
const avgRatingEl = document.getElementById('avgRating');
const localeDisplayEl = document.getElementById('localeDisplay');
const analysisSection = document.getElementById('analysisSection');
const progressFill = document.getElementById('progressFill');
const statusText = document.getElementById('statusText');
const analysisResult = document.getElementById('analysisResult');

// Event Listeners
fetchBtn.addEventListener('click', fetchReviews);
analyzeBtn.addEventListener('click', runAnalysis);
downloadBtn.addEventListener('click', downloadJSON);
closeErrorBtn.addEventListener('click', hideError);

// Filter buttons
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        filterReviews(btn.dataset.filter);
    });
});

// Locale change listener - update URL when region changes
localeSelect.addEventListener('change', updateUrlLocale);

/**
 * Fetch reviews from the API
 */
async function fetchReviews() {
    const appUrl = appUrlInput.value.trim();
    const locale = localeSelect.value;
    const limit = limitSelect.value;

    if (!appUrl) {
        showError('Please enter an App Store URL');
        return;
    }

    if (!appUrl.includes('apps.apple.com')) {
        showError('Please enter a valid App Store URL (apps.apple.com)');
        return;
    }

    showLoading(true);
    hideError();
    hideResults();

    try {
        const response = await fetch(
            `${API_BASE}/fetch-reviews?app_url=${encodeURIComponent(appUrl)}&locale=${locale}&limit=${limit}`,
            { method: 'POST' }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch reviews');
        }

        const data = await response.json();

        // Store all reviews
        currentAppName = data.app_name;
        currentReviews = data.reviews || [];

        // Display results with all reviews
        displayResults(data);

    } catch (error) {
        showError(error.message);
    } finally {
        showLoading(false);
    }
}



/**
 * Display results
 */
function displayResults(data) {
    currentAppName = data.app_name;
    currentReviews = data.reviews || [];

    appNameEl.textContent = data.app_name;
    reviewCountEl.textContent = data.total_reviews;
    localeDisplayEl.textContent = getLocaleName(data.locale);

    // Calculate rating distribution from ALL reviews
    const ratingCounts = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    currentReviews.forEach(r => ratingCounts[r.rating]++);
    const total = currentReviews.length;

    // Calculate average rating
    const avgRating = total > 0
        ? (currentReviews.reduce((sum, r) => sum + r.rating, 0) / total).toFixed(1)
        : '-';
    avgRatingEl.textContent = avgRating;

    // Update rating chart
    updateRatingChart(ratingCounts, total);

    // Enable buttons
    analyzeBtn.disabled = false;

    // Show results section
    resultsSection.classList.remove('hidden');

    // Render ALL reviews
    renderReviews(currentReviews);
}

/**
 * Render review cards
 */
function renderReviews(reviews) {
    reviewsGrid.innerHTML = reviews.map(review => `
        <div class="review-card" data-rating="${review.rating}">
            <div class="review-header">
                <div class="review-rating">
                    ${renderStars(review.rating)}
                </div>
            </div>
            ${review.title ? `<h4 class="review-title">${escapeHtml(review.title)}</h4>` : ''}
            <p class="review-body">${escapeHtml(review.body)}</p>
        </div>
    `).join('');
}

/**
 * Render star rating
 */
function renderStars(rating) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        stars += `<span class="star ${i <= rating ? '' : 'empty'}">★</span>`;
    }
    return stars;
}

/**
 * Filter reviews by rating
 */
function filterReviews(filter) {
    const cards = document.querySelectorAll('.review-card');
    cards.forEach(card => {
        if (filter === 'all' || card.dataset.rating === filter) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

/**
 * Download reviews as JSON
 */
function downloadJSON() {
    const locale = localeSelect.value;

    const data = {
        app_name: currentAppName,
        locale: locale,
        total_reviews: currentReviews.length,
        exported_at: new Date().toISOString(),
        reviews: currentReviews.map(r => ({
            rating: r.rating,
            title: r.title || '',
            body: r.body || '',
            date: r.date || null
        }))
    };

    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    const safeName = currentAppName.toLowerCase().replace(/[^a-z0-9]+/g, '_');
    a.download = `${safeName}_${locale}_reviews.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Run AI analysis
 */
async function runAnalysis() {
    const appUrl = appUrlInput.value.trim();
    const limit = limitSelect.value;

    analysisSection.classList.remove('hidden');
    analyzeBtn.disabled = true;
    progressFill.style.width = '0%';
    statusText.textContent = 'Starting analysis...';

    // Scroll to analysis section
    analysisSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    try {
        // Create analysis job
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                app_url: appUrl,
                platform: 'ios',
                options: { review_limit: parseInt(limit) }
            })
        });

        if (!response.ok) {
            throw new Error('Failed to start analysis');
        }

        const data = await response.json();
        currentAnalysisId = data.analysis_id;

        // Poll for status
        pollAnalysisStatus();

    } catch (error) {
        showError(error.message);
        analyzeBtn.disabled = false;
    }
}

/**
 * Poll analysis status
 */
async function pollAnalysisStatus() {
    if (!currentAnalysisId) return;

    try {
        const response = await fetch(`${API_BASE}/status/${currentAnalysisId}`);
        const data = await response.json();

        progressFill.style.width = `${data.progress || 0}%`;
        statusText.textContent = `Status: ${data.status} (${data.progress || 0}%)`;

        if (data.status === 'completed') {
            fetchAnalysisResult();
        } else if (data.status === 'failed') {
            showError(`Analysis failed: ${data.error}`);
            analyzeBtn.disabled = false;
        } else {
            // Continue polling
            setTimeout(pollAnalysisStatus, 2000);
        }
    } catch (error) {
        showError('Failed to check analysis status');
        analyzeBtn.disabled = false;
    }
}

/**
 * Fetch analysis result
 */
async function fetchAnalysisResult() {
    try {
        const response = await fetch(`${API_BASE}/result/${currentAnalysisId}`);
        const data = await response.json();

        displayAnalysisResult(data.result);
        analyzeBtn.disabled = false;

    } catch (error) {
        showError('Failed to fetch analysis result');
        analyzeBtn.disabled = false;
    }
}

/**
 * Display analysis result
 */
function displayAnalysisResult(result) {
    analysisResult.classList.remove('hidden');
    analysisResult.innerHTML = `
        <div class="analysis-summary">
            <h3>Summary</h3>
            <p>${escapeHtml(result.summary)}</p>
        </div>
        
        <div class="analysis-grid">
            <div class="analysis-card">
                <h4>Sentiment</h4>
                <div class="sentiment-bar">
                    <div class="sentiment-positive" style="width: ${result.sentiment_breakdown.positive}%">
                        ${result.sentiment_breakdown.positive}% 👍
                    </div>
                    <div class="sentiment-neutral" style="width: ${result.sentiment_breakdown.neutral}%">
                        ${result.sentiment_breakdown.neutral}%
                    </div>
                    <div class="sentiment-negative" style="width: ${result.sentiment_breakdown.negative}%">
                        ${result.sentiment_breakdown.negative}% 👎
                    </div>
                </div>
            </div>
            
            <div class="analysis-card">
                <h4>Top Issues</h4>
                <ul>
                    ${result.top_issues.slice(0, 5).map(issue =>
        `<li><strong>${issue.severity.toUpperCase()}</strong>: ${escapeHtml(issue.issue)} (${issue.frequency}x)</li>`
    ).join('')}
                </ul>
            </div>
            
            <div class="analysis-card">
                <h4>Feature Requests</h4>
                <ul>
                    ${result.feature_requests.slice(0, 5).map(feature =>
        `<li>${escapeHtml(feature.feature)} (${feature.count}x)</li>`
    ).join('')}
                </ul>
            </div>
            
            <div class="analysis-card">
                <h4>Recommended Actions</h4>
                <ul>
                    ${result.recommended_actions.slice(0, 5).map(action =>
        `<li><strong>[${action.priority.toUpperCase()}]</strong> ${escapeHtml(action.action)}</li>`
    ).join('')}
                </ul>
            </div>
        </div>
    `;
}

// Helper functions
function showLoading(show) {
    loadingDiv.classList.toggle('hidden', !show);
}

function showError(message) {
    errorMessage.textContent = message;
    errorDiv.classList.remove('hidden');
}

function hideError() {
    errorDiv.classList.add('hidden');
}

function hideResults() {
    resultsSection.classList.add('hidden');
    analysisSection.classList.add('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getLocaleName(locale) {
    const names = {
        'en-US': '🇺🇸 USA',
        'en-GB': '🇬🇧 UK',
        'de-DE': '🇩🇪 Germany',
        'fr-FR': '🇫🇷 France',
        'es-ES': '🇪🇸 Spain',
        'it-IT': '🇮🇹 Italy',
        'pt-BR': '🇧🇷 Brazil',
        'ja-JP': '🇯🇵 Japan',
        'ko-KR': '🇰🇷 Korea',
        'zh-CN': '🇨🇳 China',
        'tr-TR': '🇹🇷 Turkey'
    };
    return names[locale] || locale;
}

/**
 * Update rating distribution chart
 */
function updateRatingChart(ratingCounts, total) {
    for (let i = 1; i <= 5; i++) {
        const count = ratingCounts[i] || 0;
        const percentage = total > 0 ? (count / total * 100) : 0;

        const bar = document.getElementById(`bar${i}`);
        const countEl = document.getElementById(`count${i}`);

        if (bar) bar.style.width = `${percentage}%`;
        if (countEl) countEl.textContent = count;
    }
}

/**
 * Update URL when locale/region changes
 * Changes URL from https://apps.apple.com/tr/app/name/id123?l=tr
 * to the new locale format
 */
function updateUrlLocale() {
    const url = appUrlInput.value.trim();
    if (!url || !url.includes('apps.apple.com')) return;

    const newLocale = localeSelect.value;
    // Get the country code from locale (e.g., 'en-US' -> 'us', 'tr-TR' -> 'tr')
    const countryCode = newLocale.split('-')[1]?.toLowerCase() || newLocale.split('-')[0]?.toLowerCase() || 'us';

    let updatedUrl = url;

    // Update the country code in the path (e.g., /tr/ or /us/)
    // Pattern: /apps.apple.com/XX/ where XX is country code
    updatedUrl = updatedUrl.replace(
        /apps\.apple\.com\/([a-z]{2})\//i,
        `apps.apple.com/${countryCode}/`
    );

    // Update or add the ?l= parameter
    if (updatedUrl.includes('?l=')) {
        // Replace existing l= parameter
        updatedUrl = updatedUrl.replace(/([?&])l=[a-z]{2}/i, `$1l=${countryCode}`);
    } else if (updatedUrl.includes('?')) {
        // Add l= to existing query string
        updatedUrl = updatedUrl + `&l=${countryCode}`;
    } else {
        // Add new query string
        updatedUrl = updatedUrl + `?l=${countryCode}`;
    }

    appUrlInput.value = updatedUrl;
}
