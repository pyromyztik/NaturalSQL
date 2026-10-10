# NaturalSQL: Universal Database Assistant

A deterministic safety, verification, and repair pipeline between an LLM and live databases (**Oracle**, **PostgreSQL**, **MySQL**).

Instead of executing raw LLM-generated SQL directly on your database, **NaturalSQL** parses the query into an **Abstract Syntax Tree (AST)** using `sqlglot`, validates it against the schema catalog, auto-patches common model omissions, and enforces a strict **Human-in-the-Loop Approval Gate** before any data-modifying queries (`INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP`) are executed.

---

## Key Capabilities

1. **Universal Database Connectivity**:
   Connect to any database using industry-standard Connection URIs:
   - **Oracle**: `oracle://user:password@localhost:1521/FREEPDB1` *(or terminal EZConnect: `user/password@host:1521/service`)*
   - **PostgreSQL**: `postgresql://postgres:password@localhost:5432/dbname`
   - **MySQL**: `mysql://root:password@localhost:3306/dbname`
2. **Minimal Code & Universal Introspection**:
   Powered by SQLAlchemy universal reflection (`inspect(engine)`) with pure-Python drivers (`oracledb` in thin mode, `psycopg2`, `pymysql`).
3. **Dual Interfaces**:
   - **Web Application**: Interactive chat interface with live streaming tokens, schema drawer, and data grids.
   - **Command Line Interface (CLI)**: Interactive shell (`cli.py`) and scriptable one-shot execution.
4. **Human-in-the-Loop Safety Gatekeeper**:
   - `SELECT` queries compile and execute automatically.
   - Any mutation (`INSERT`, `UPDATE`, `DELETE`, etc.) halts and requires explicit user confirmation before touching the database.
5. **Blank by Default & Privacy**:
   Starts with no pre-connected databases. Includes a one-click / one-command action to forget all saved databases.

---

## Quickstart

### 1. Launch the Web Application
```powershell
python run_app.py
```
*Opens automatically at `http://127.0.0.1:8000`.*

### 2. Run the Interactive CLI Shell
```powershell
python cli.py
```

Inside the CLI shell:
```text
NaturalSQL (oracle)> Find all employees earning over 60000
NaturalSQL (oracle)> /tables
NaturalSQL (oracle)> /connect postgresql://postgres:password@localhost:5432/postgres
NaturalSQL (oracle)> /forget
NaturalSQL (oracle)> /exit
```

### 3. One-Shot CLI Execution
```powershell
# Query Oracle container
python cli.py --conn "oracle://user:password@localhost:1521/FREEPDB1" --query "How many employees are there?"

# Query local PostgreSQL
python cli.py --conn "postgresql://postgres:password@localhost:5432/postgres" --query "List all tables"
```

### 4. Manage Saved Connections
```powershell
# List saved connections
python cli.py --list

# Forget all saved connections
python cli.py --forget
```
