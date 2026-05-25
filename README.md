# 🤖 GitReview AI: Multi-Agent Code Review & Codebase Memory

GitReview AI is a professional-grade, resume-worthy, multi-agent code review platform built for hackathons and production software workflows. Leveraging **FastAPI**, **Streamlit**, **LangGraph**, and **ChromaDB**, it conducts deep structural audits on pull requests by splitting diff blocks, fanning out review hunks to parallel specialist AI agents, publishing batched inline suggestions directly to GitHub, and preserving codebase semantic memory offline via RAG.

---

## 🌟 Core Highlights

- **🐙 Dual Integration Modes**: Works fully automatically via real-time GitHub Webhook event listeners, or on-demand using a simple manual "PR Review Console" (perfect for live hackathon presentations).
- **🕸️ LangGraph Multi-Agent Orchestration**: Implements parallel branching (fan-out) to execute four specialist reviewer nodes simultaneously:
  - **🕷️ Bug Detection Agent**: Focuses on runtime flaws, edge-case failures, unhandled exceptions, and type errors.
  - **🔒 Security Auditor Agent**: Audit OWASP Top 10 vulnerabilities, hardcoded API secrets, sanitization issues, and plaintext logs.
  - **⚡ Performance Profiler Agent**: Evaluates latency loops, resource leakages, N+1 query patterns, and async-blocking routines.
  - **🎨 Architecture & Refactoring Agent**: Reviews DRY compliance, SOLID patterns, readability, naming conventions, and logs.
- **📝 Automated Synthesizer Node**: Combines individual findings, removes duplicates, compiles a detailed markdown executive report, and calculates a dynamic **0-100 Software Health Score** based on severity deductions.
- **💡 Direct Inline Suggesters**: Batches findings into a single GitHub Pull Request Review submission, generating markdown ````suggestion ```` code replacements that authors can commit with a single click inside GitHub!
- **📚 Semantic Codebase Chat (RAG)**: Indexes repositories in ChromaDB using local HuggingFace embeddings (`all-MiniLM-L6-v2`) on connect. Provides a developer chatbot to query structures or draft code complying with repository design patterns.
- **📊 Modern Glassmorphic Dashboard**: A premium dark UI featuring analytical visual cards, issue distribution pie charts, score historical trend lines, and codebase high-risk hotspots tracking.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend UI** | Streamlit | BESPOKE Dark UI with HTML/CSS glassmorphic styles |
| **Backend API** | FastAPI | High-concurrency async endpoints with Pydantic validation |
| **AI Graph** | LangGraph & LangChain | Fan-out/Fan-in state machines using ChatGroq client |
| **RAG Memory** | ChromaDB & SentenceTransformers | CPU-friendly, 100% offline, syntax-aware code embeddings |
| **Database** | SQLite & SQLAlchemy | Non-blocking database session layers using `aiosqlite` |

---

## 🏗️ Multi-Agent Architecture

```
                       [ GitHub PR Opened / Manual Trigger ]
                                       │
                                       ▼
                       [ Parsed Modified Line Splits ]
                                       │
                ┌──────────────────────┼──────────────────────┬──────────────────────┐
                │                      │                      │                      │
                ▼                      ▼                      ▼                      ▼
        [ 🕷️ Bug Specialist ]   [ 🔒 Security Auditor ]  [ ⚡ Latency Profiler ] [ 🎨 Refactoring Agent ]
                │                      │                      │                      │
                └──────────────────────┼──────────────────────┴──────────────────────┘
                                       │
                                       ▼
                       [ 📝 Executive Synthesizer Node ]
                                       │
                                ┌──────┴──────┐
                                ▼             ▼
                     [ SQLite & Dashboard ] [ GitHub Inline Comments ]
```

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have **Python 3.10 or higher** installed.

### 2. Environment Settings
Make a copy of `.env.example` as `.env` at the root folder:
```bash
copy .env.example .env
```
*(By default, `DEMO_MODE=true` is enabled, allowing you to run and present the entire system fully offline with pre-compiled high-fidelity code reviews and codebase RAG simulations!)*

To activate live AI runs, configure these credentials:
- **Groq API Key**: Obtain a free key at [console.groq.com](https://console.groq.com/) (Uses `llama-3.3-70b-versatile`).
- **GitHub PAT / OAuth credentials**: Create a Personal Access Token with `repo` scope at [github.com/settings/tokens](https://github.com/settings/tokens).

### 3. Installation
Establish a python virtual environment, activate it, and install all pinned dependencies:

```bash
# Create environment
python -m venv venv

# Activate on Windows Powershell
.\venv\Scripts\Activate.ps1

# Activate on Windows Git Bash / Linux
source venv/Scripts/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Running the Application
Launch both backend and frontend servers simultaneously using our unified automation runner:
```bash
python run.py
```
This script will:
1. Verify the presence of `.env` configurations.
2. Initialize SQLite schemas asynchronously.
3. Boot the FastAPI API on `http://127.0.0.1:8000`.
4. Launch the Streamlit dashboard on `http://127.0.0.1:8501`.

---

## ⚡ Hackathon Live Presentation Tips

1. **💡 Toggle Demo Mode (`DEMO_MODE=true`)**: 
   Live networking bottlenecks or rate limits are common presentation hazards. Keep `DEMO_MODE=true` enabled in your `.env` to demonstrate repository connecting, vector database crawling, real-time multi-agent timelines, and interactive finding card renders instantly and securely—all without requiring an active internet connection or loading external API keys.
2. **🔌 Live GitHub Hook Tunnelling (ngrok)**:
   To run actual live reviews triggered directly on GitHub actions, start an `ngrok` tunnel on the local backend port:
   ```bash
   ngrok http 8000
   ```
   Copy the secure tunnel URL (e.g. `https://random-subdomain.ngrok-free.app`) and set it as `APP_URL` in your `.env`. When you connect a repository, GitReview AI will register webhooks on GitHub pointing to this tunnel, enabling real-time review posts directly to live pull request code branches!
