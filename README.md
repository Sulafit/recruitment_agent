# AI Recruiting Agent

AI-powered candidate matching system that helps recruiters process resumes, match them with job openings, and recommend suitable candidates.

## Features

- **Automated Email Integration**: Fetch resumes from email (IMAP) automatically
- **Multi-format Resume Parsing**: Supports PDF, DOCX, images using Tesseract OCR
- **Dual Matching Approaches**:
  - **Embedding-based**: Fast semantic matching using Qwen embeddings and cosine similarity
  - **LLM-based**: AI-powered matching with Mistral LLM providing explanations
- **REST API**: FastAPI backend with comprehensive endpoints
- **Web Interface**: Minimal Streamlit frontend for easy interaction
- **Multi-language Support**: Works with both Russian and English resumes
- **Docker Support**: Complete containerization for easy deployment

## Architecture

```
recruiting_agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration management
│   │   ├── models.py            # Pydantic data models
│   │   ├── email_client.py      # IMAP email integration
│   │   ├── resume_parser.py     # Resume parsing with Tesseract
│   │   └── matching/
│   │       ├── embedding_matcher.py  # Qwen embeddings + cosine similarity
│   │       ├── llm_matcher.py        # Mistral LLM matching
│   │       └── matcher.py            # Main matching interface
│   └── requirements.txt
├── frontend/
│   ├── streamlit_app.py         # Streamlit web interface
│   └── requirements.txt
├── data/
│   ├── jobs/                    # Job descriptions (JSON)
│   └── resumes/                 # Parsed resumes
├── docker-compose.yml
├── Dockerfile
└── .env                         # API keys and configuration
```

## Processing Pipeline

1. **Resume Collection**
   - IMAP client connects to email
   - Downloads attachments (PDF, DOCX, images)
   - Saves to `data/resumes/`

2. **Resume Parsing**
   - Extracts text using Tesseract OCR (for images/scanned PDFs)
   - Parses structure: skills, experience, education
   - Uses NLP for keyword extraction

3. **Candidate Matching**
   - **Method 1 - Embeddings**:
     - Generate embeddings using Qwen/Qwen3-Embedding-0.6B
     - Calculate cosine similarity between job and resumes
     - Return ranked candidates
   - **Method 2 - LLM**:
     - Send job + resume to Mistral LLM
     - Get relevance score (0-1) with explanation
     - Return ranked candidates with reasoning

4. **API Response**
   - Returns top-5 candidates with scores
   - Includes matching skills
   - LLM method includes explanations

## Installation

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (for containerized deployment)
- Tesseract OCR (for local development)

### Local Setup

1. Clone the repository
```bash
cd recruiting_agent
```

2. Configure environment variables
```bash
# Edit .env file with your credentials
EMAIL_PASSWORD=your_gmail_app_password
HF_TOKEN=your_huggingface_token
MISTRAL_API_KEY=your_mistral_api_key
```

3. Install Tesseract OCR
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus

# macOS
brew install tesseract tesseract-lang
```

4. Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

5. Install frontend dependencies
```bash
cd ../frontend
pip install -r requirements.txt
```

### Docker Setup

1. Configure `.env` file with your credentials

2. Build and run with Docker Compose
```bash
docker-compose up --build
```

This will start:
- Backend API on http://localhost:8000
- Frontend UI on http://localhost:8501

## Usage

### 1. Add Job Descriptions

Create JSON files in `data/jobs/`:

```json
{
  "id": "job_001",
  "title": "Senior Python Developer",
  "description": "Job description...",
  "requirements": "Requirements...",
  "tech_stack": ["Python", "FastAPI", "Docker"]
}
```

### 2. Add Resumes

Option A: Manual upload
- Place resume files in `data/resumes/`

Option B: Email integration
- Send resumes to configured email
- Use API endpoint: `POST /fetch-resumes`
- Or click "Fetch New Resumes" in UI

### 3. Get Recommendations

#### Via REST API

```bash
# Using job ID
curl "http://localhost:8000/recommendations?job_id=job_001&method=embedding&top_k=5"

# Using custom job description
curl "http://localhost:8000/recommendations?job_text=Looking%20for%20Python%20developer&method=llm&top_k=5"
```

#### Via Web Interface

1. Open http://localhost:8501
2. Select matching method (embedding/llm)
3. Choose job or enter custom description
4. Click "Find Candidates"
5. View ranked results with scores

## API Endpoints

### `GET /`
Root endpoint with API information

### `GET /recommendations`
Get candidate recommendations

**Parameters:**
- `job_id` (optional): Job ID from data/jobs/
- `job_text` (optional): Custom job description
- `method` (required): "embedding" or "llm"
- `top_k` (optional): Number of candidates (default: 5)

**Response:**
```json
{
  "job_id": "job_001",
  "job_title": "Senior Python Developer",
  "method": "llm",
  "candidates": [
    {
      "candidate_id": "resume_1.pdf",
      "candidate_name": "John Doe",
      "score": 0.92,
      "matching_skills": ["Python", "FastAPI", "Docker"],
      "explanation": "Strong match with 5+ years Python experience..."
    }
  ]
}
```

### `GET /jobs`
List all available jobs

### `GET /resumes`
List all parsed resumes

### `POST /fetch-resumes`
Fetch new resumes from email

## Matching Methods

### 1. Embedding-based Matching
- **Speed**: Fast (seconds)
- **Model**: Qwen/Qwen3-Embedding-0.6B
- **Metric**: Cosine similarity
- **Use case**: Quick filtering, large candidate pools

### 2. LLM-based Matching
- **Speed**: Slower (API calls)
- **Model**: Mistral Small
- **Metric**: AI-generated score (0-1)
- **Benefits**: Provides explanations, better semantic understanding
- **Use case**: Final selection, detailed evaluation

## Configuration

Edit `.env` file:

```bash
# Email
EMAIL_ADDRESS=sultan.mukhtar1404@gmail.com
EMAIL_PASSWORD=your_app_password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993

# API Keys
HF_TOKEN=your_huggingface_token
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_MODEL=mistral-small-2506

# Paths
RESUMES_DIR=data/resumes
JOBS_DIR=data/jobs
```

## Examples

### Example 1: Find Python Developers

```python
import requests

response = requests.get(
    "http://localhost:8000/recommendations",
    params={
        "job_id": "job_001",
        "method": "llm",
        "top_k": 5
    }
)

results = response.json()
for i, candidate in enumerate(results['candidates'], 1):
    print(f"{i}. {candidate['candidate_name']} - Score: {candidate['score']}")
    print(f"   Explanation: {candidate['explanation']}")
```

### Example 2: Custom Job Search

```python
job_description = """
Looking for Full Stack Developer with:
- React and Node.js experience
- Knowledge of MongoDB
- Docker and Kubernetes skills
"""

response = requests.get(
    "http://localhost:8000/recommendations",
    params={
        "job_text": job_description,
        "method": "embedding",
        "top_k": 3
    }
)
```

## Technologies Used

### Backend
- **FastAPI**: REST API framework
- **Pytesseract**: OCR for resume parsing
- **HuggingFace**: Qwen embeddings
- **Mistral AI**: LLM for intelligent matching
- **PyPDF2, python-docx**: Document parsing

### Frontend
- **Streamlit**: Web interface

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration

## Performance

- **Embedding matching**: ~2-5 seconds for 100 resumes
- **LLM matching**: ~10-30 seconds for 10 resumes (API dependent)
- **Resume parsing**: ~1-3 seconds per file

## Limitations

- Email integration requires app-specific password (Gmail)
- Tesseract OCR accuracy depends on document quality
- LLM matching has API rate limits and costs
- Supports PDF, DOCX, TXT, and image formats only

## Future Improvements

- Background job processing queue
- Resume deduplication
- Advanced NER for better entity extraction
- Caching for faster repeated queries
- Multi-stage matching pipeline

## License

MIT License

## Author

AI Recruiting Agent MVP v1.0.0
