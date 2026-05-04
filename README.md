# 🏛️ TenderAudit
### AI-Powered Government Tender Eligibility Evaluation System

A semi-automatic, explainable AI system built with Streamlit + Groq (Llama 3.1) for evaluating bidder eligibility in government procurement.

---

## 📁 Project Structure

```
tenderaudit/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── README.md                 # This file
└── modules/
    ├── __init__.py
    ├── document_processor.py # PDF & image text extraction (OCR)
    ├── llm_engine.py         # Groq LLM integration + prompts
    └── pdf_exporter.py       # PDF report generation
```

---

## ⚙️ Setup Instructions

### Step 1: Prerequisites

Make sure you have Python 3.9+ installed.

Install system dependencies for OCR:

**Ubuntu / Debian (Linux):**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

**macOS:**
```bash
brew install tesseract poppler
```

**Windows:**
- Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Download Poppler: https://github.com/oschwartz10612/poppler-windows/releases
- Add both to your system PATH

---

### Step 2: Get Your Free Groq API Key

1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up for a free account
3. Navigate to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

---

### Step 3: Install Python Dependencies

```bash
# Clone or download this folder, then:
cd tenderaudit

# Create virtual environment (recommended)
python -m venv venv

# Activate it:
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

### Step 4: Set Your API Key

**Option A — .env file (recommended):**
```bash
cp .env.example .env
# Edit .env and paste your Groq API key:
# GROQ_API_KEY=gsk_your_key_here
```

**Option B — Enter in the app UI:**
You can also paste your API key directly into the sidebar when the app runs.

---

### Step 5: Run the App

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 🚀 How to Use TenderAudit

### Workflow (4 Steps):

**1. Upload Tender Document**
- Upload the government tender PDF
- Enter a tender name/reference number
- Click "Extract Text & Identify Criteria"
- AI extracts eligibility criteria — review, edit, add, or delete any rows
- Click "Save Criteria & Continue"

**2. Upload Bidder Documents**
- Enter the bidder/company name
- Upload their documents (financial statements, certificates, experience letters, etc.)
- Click "Add Bidder" — supports bulk PDF/image upload per bidder
- Repeat for all bidders (3–5 recommended for demos)

**3. Run Evaluation**
- Click "Run Full Evaluation"
- AI evaluates each bidder against each criterion
- Results include: Status, Extracted Value, Source Page, Confidence %

**4. View Results & Export**
- Color-coded dashboard: 🟢 Eligible · 🟡 Needs Review · 🔴 Not Eligible
- Click any bidder to see detailed criterion-by-criterion breakdown
- Override AI decisions at criterion level or overall bidder level
- Export a complete PDF audit report

---

## 🤖 LLM Prompts

### Prompt 1: Criteria Extraction
Located in `modules/llm_engine.py` → `CRITERIA_EXTRACTION_PROMPT`

Instructs the LLM to extract all eligibility criteria as a structured JSON array with fields: `criterion_name`, `type` (Financial/Technical/Compliance), `required_value`, `unit`, `description`.

### Prompt 2: Bidder Evaluation
Located in `modules/llm_engine.py` → `BIDDER_EVALUATION_PROMPT`

For each criterion, the LLM extracts the relevant value from bidder documents and returns: `extracted_value`, `source_page`, `status` (Pass/Fail/Needs Review), `confidence` (0–100), `reasoning`.

---

## 🔧 Configuration

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Your Groq API key |

The LLM model used is `llama-3.1-8b-instant` — fast and free tier eligible.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web application framework |
| `groq` | Groq API client for Llama 3.1 |
| `pdfplumber` | Digital PDF text extraction |
| `pdf2image` | Convert PDF pages to images for OCR |
| `pytesseract` | OCR engine wrapper |
| `Pillow` | Image processing |
| `reportlab` | PDF report generation |
| `pandas` | Data manipulation |
| `python-dotenv` | Environment variable loading |

---

## ⚠️ Troubleshooting

**"tesseract is not installed or not in PATH"**
→ Install Tesseract OCR (see Step 1)

**"Unable to get page count. Is poppler installed?"**
→ Install Poppler (see Step 1)

**"Error connecting to Groq API"**
→ Check your API key is correct and you have internet access

**OCR quality is poor on scanned documents**
→ Ensure scanned PDFs are at least 200 DPI. The app uses `--psm 6` mode for best results.

---

## 🏆 Hackathon Notes

- **Demo tip:** Prepare 1 tender PDF + 3–5 bidder PDFs in advance for a smooth demo
- **Speed:** Groq Llama 3.1 8B is extremely fast (~2–3 sec per bidder evaluation)
- **Explainability:** Every decision has a source page reference and reasoning — ideal for procurement transparency
- **Override feature:** Shows human-in-the-loop design, a key differentiator for government use

---

*Built with ❤️ for transparent, auditable government procurement.*
