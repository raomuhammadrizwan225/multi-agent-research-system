# ResearchMind - Multi-Agent AI Research System

ResearchMind is a simple multi-stage AI research application. A user enters a research question, the system finds relevant web sources, reads those sources, writes a structured report, and then reviews the report with a critic chain.

## How it works

The application runs four stages in order:

1. **Search Agent** - uses Tavily Search to find up to five relevant URLs from different domains.
2. **Reader Agent** - extracts content from the same URLs and creates a short factual summary for each source.
3. **Writer Chain** - combines the search results and reader summaries into a structured research report with Introduction, Key Findings, Conclusion, and Sources.
4. **Critic Chain** - reviews the final report and returns a score, strengths, areas to improve, and a final verdict.

## Technologies used

- Python 3.11 recommended
- LangChain
- Groq / `ChatGroq`
- Tavily Search and Extract
- Requests
- Beautiful Soup 4
- HTML
- CSS
- Vanilla JavaScript
- Python built-in HTTP server

## Project structure

```text
Multi-agent-research-system/
│
├── agents.py
├── tools.py
├── pipeline.py
├── web_server.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
└── frontend/
    ├── index.html
    ├── styles.css
    └── app.js
```

## Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd Multi-agent-research-system
```

### 2. Create a virtual environment

Windows:

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

If you copied the project from another folder or computer, create a fresh virtual environment instead of copying the old `.venv` folder.

### 3. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root. You can copy `.env.example` and replace the placeholder values:

```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

Never commit your real `.env` file or API keys to GitHub.

## Run the web application

Start the server:

```bash
python web_server.py
```

The terminal should show:

```text
ResearchMind HTML/CSS/JavaScript UI
Local URL: http://127.0.0.1:8501
Press Ctrl+C to stop the server.
```

Open this address in your browser:

```text
http://127.0.0.1:8501
```

Enter a research question and click **Run Research Pipeline**.

## Run the terminal version

You can also run the same research workflow directly in the terminal:

```bash
python pipeline.py
```

Enter a research topic when prompted.

## Expected report structure

The Writer Chain is instructed to return a clean report in this order:

```text
Introduction

Key Findings
1. Finding title
2. Finding title
3. Finding title

Conclusion

Sources
1. https://...
2. https://...
```

The Critic Chain is displayed after the report and includes:

- Overall score out of 10
- Strengths
- Areas to improve
- Final verdict

## Main dependencies

The required Python packages are listed in `requirements.txt`:

```text
langchain
langchain-core
langchain-groq
tavily-python
beautifulsoup4
requests
python-dotenv
```

## Common issues

### `No module named 'bs4'`

Install the project requirements inside the active virtual environment:

```bash
python -m pip install -r requirements.txt
```

### API key error

Check that `.env` exists in the project root and contains valid Groq and Tavily API keys.

### Port 8501 is already in use

Stop the old process or set another port before starting the server.

Windows CMD:

```bat
set RESEARCHMIND_PORT=8502
python web_server.py
```

PowerShell:

```powershell
$env:RESEARCHMIND_PORT="8502"
python web_server.py
```

### Browser still shows an old Streamlit page

This project now uses HTML, CSS, JavaScript, and `web_server.py`. Open a fresh browser tab at the URL printed by `web_server.py` and perform a hard refresh if necessary.

## Security

`.gitignore` excludes `.env`, virtual environments, Python cache folders, and `.pyc` files. Keep real API keys private.
