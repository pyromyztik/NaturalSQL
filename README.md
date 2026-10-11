# NaturalSQL: Universal Database Assistant

A deterministic safety, verification, and repair pipeline between an LLM and live databases (**Oracle**, **PostgreSQL**, **MySQL**, **SQLite**).

Instead of executing raw LLM-generated SQL directly on your database, **NaturalSQL** parses the query into an **Abstract Syntax Tree (AST)** using `sqlglot`, validates it against the schema catalog, auto-patches common model omissions, and enforces a strict **Human-in-the-Loop Approval Gate** before any data-modifying queries (`INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP`) are executed.

---

## Key Capabilities

1. **Universal Database Connectivity**:
   Connect to any database using industry-standard Connection URIs.
2. **Universal Introspection & Reflection**:
   Powered by SQLAlchemy universal reflection (`inspect(engine)`) with pure-Python drivers (`oracledb` in thin mode, `psycopg2`, `pymysql`).
3. **AST Gatekeeper & Self-Healing Pipeline**:
   - Syntactic and semantic validation before SQL execution.
   - Automatic detection of missing `GROUP BY` columns, invalid `CROSS JOIN ... ON` syntax, and missing `LIMIT` guards.
   - Multi-turn surgical feedback loop with the model to repair schema hallucinations automatically.
4. **Dual Interfaces**:
   - **Web Application**: Interactive chat interface with live streaming tokens, schema drawer, approval banners, and data grids.
   - **Command Line Interface (CLI)**: Interactive shell (`cli.py`) and scriptable one-shot execution.
5. **Human-in-the-Loop Safety Gatekeeper**:
   - `SELECT` queries compile and execute automatically.
   - Any mutation (`INSERT`, `UPDATE`, `DELETE`, `DDL`) halts and requires explicit user confirmation before touching the database.
6. **Zero Pre-connections & Privacy**:
   Starts with no pre-connected databases. Includes a one-click or one-command action to forget all saved databases.

---

## Prerequisites

Before running NaturalSQL, ensure you have:

- **Python 3.10+** installed
- **Node.js 18+ & npm** installed *(required to build the frontend)*
- **[Ollama](https://ollama.ai)** installed and running locally
- Access to a target database (**Oracle 19c/21c/23c**, **PostgreSQL**, **MySQL**, or **SQLite**)

---

## Quickstart & Installation

### 1. Clone & Set Up Python Environment

```powershell
# Clone the repository
git clone https://github.com/your-username/NaturalSQL.git
cd NaturalSQL

# Create and activate a virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up the Ollama Model

Make sure Ollama is running (`ollama serve`), then build the custom deterministic SQL model using the provided `Modelfile`:

```powershell
ollama create naturalsql -f Modelfile
```

> **Note:** The `Modelfile` inherits from `qwen3.5:9b` by default with low temperature (`0.05`), high context window (`16384`), and a custom system prompt. Make sure you have pulled the base model or adjust the `FROM` line in `Modelfile` to your preferred local model.

### 3. Build Frontend (One-Time Setup)

The frontend is a Vite + React application in the `frontend/` directory. Install its packages:

```powershell
cd frontend
npm install
npm run build
cd ..
```

*(Note: `run_app.py` will also automatically detect and trigger `npm run build` if the `frontend/dist` folder does not exist yet.)*

---

## How to Run

### Option 1: Launch the Full Web Application (Recommended)

Run the unified runner script:

```powershell
python run_app.py
```

- Starts the FastAPI backend (`server:app`) on port `8000`.
- Serves the compiled production React frontend.
- Automatically opens your default web browser at `http://127.0.0.1:8000`.

---

### Option 2: Run in Development Mode (Live Hot-Reload)

If you are modifying frontend UI components or backend API routes, run both servers concurrently:

**Terminal 1 (Backend API):**
```powershell
python server.py
```
*API runs at `http://127.0.0.1:8000` with auto-reload.*

**Terminal 2 (Frontend with Vite HMR):**
```powershell
cd frontend
npm run dev
```
*Vite dev server runs at `http://localhost:5173` with instant hot-reloading.*

---

### Option 3: Run the Interactive CLI Shell

NaturalSQL includes a standalone terminal interface:

```powershell
python cli.py
```

Inside the CLI shell, you can query your active database or use slash commands:

```text
NaturalSQL (oracle)> Find all products in Electronics category priced above 50
NaturalSQL (oracle)> /tables
NaturalSQL (oracle)> /schema products
NaturalSQL (oracle)> /connect postgresql://postgres:password@localhost:5432/postgres
NaturalSQL (postgres)> /list
NaturalSQL (postgres)> /forget
NaturalSQL> /exit
```

---

### Option 4: Scriptable One-Shot CLI Execution

Run queries directly from CI/CD, scripts, or terminal commands:

```powershell
# Query an Oracle database
python cli.py --conn "oracle://user:password@localhost:1521/FREEPDB1" --query "How many products are in stock?"

# Query a PostgreSQL database
python cli.py --conn "postgresql://postgres:password@localhost:5432/mydb" --query "Show top 5 customers by order count"

# List saved connections
python cli.py --list

# Forget all saved connections
python cli.py --forget
```

---

## Database Connection URI Formats

When connecting via the Web UI Modal or the CLI, use standard URIs:

| Database | Supported Formats |
| :--- | :--- |
| **Oracle** | `oracle://user:password@localhost:1521/FREEPDB1`<br>`user/password@localhost:1521/FREEPDB1` *(EZConnect)* |
| **PostgreSQL** | `postgresql://postgres:password@localhost:5432/dbname` |
| **MySQL** | `mysql://root:password@localhost:3306/dbname` |
| **SQLite** | `sqlite:///C:/path/to/database.db` *(Windows)*<br>`sqlite:////path/to/database.db` *(Linux/macOS)* |

---

## Configuration & Environment Variables

You can optionally configure settings in [`src/config.py`](src/config.py) or via environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `OLLAMA_HOST` | `http://localhost:11434` | URL to your running Ollama server |
| `OLLAMA_MODEL` | `naturalsql` | Model name created from `Modelfile` |
| `OLLAMA_TIMEOUT` | `300` | Generation timeout in seconds |
| `OLLAMA_MAX_TOKENS` | `8192` | Max prediction tokens for complex queries |
| `OLLAMA_NUM_CTX` | `16384` | Context window size for large schemas |
| `DEFAULT_LIMIT` | `50` | Safety `LIMIT` auto-injected onto unbounded `SELECT` queries |
| `MAX_SURGICAL_RETRIES` | `2` | Max AST compiler repair attempts before erroring |