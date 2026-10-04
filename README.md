# NaturalSQL: Compiler-Style Text-to-SQL Gatekeeper

A deterministic safety, verification, and repair pipeline between an LLM and PostgreSQL.

Instead of executing raw LLM-generated SQL directly on your database, **NaturalSQL** parses the query into an **Abstract Syntax Tree (AST)** using `sqlglot`, validates it against your schema catalog, auto-patches common model omissions (such as missing `GROUP BY` or `LIMIT`), and provides surgical feedback loops for hallucinated identifiers.

---

## Architecture Overview

```
User Question (Natural Language)
             │
             ▼
    Local LLM (Qwen 3.5 9B via Ollama)
             │
         (Raw SQL)
             ▼
┌────────────────────────────────────────────────────────┐
│             AST COMPILER GATEKEEPER                    │
│                                                        │
│  1. Syntax Parsing (sqlglot Postgres dialect)          │
│  2. Security Gate (Strictly blocks DDL / DML)          │
│  3. Catalog Validation (Tables, columns, aliases)      │
│  4. Tier 1 Auto-Patching (Zero extra tokens):          │
│     - Auto-reconstruct missing GROUP BY projections    │
│     - Auto-inject safety LIMIT 50                      │
└────────────┬────────────────────────────┬──────────────┘
             │ (Valid / Auto-Patched)     │ (Catalog Mismatch)
             ▼                            ▼
   [Verified PostgreSQL]        [Tier 2 Surgical Feedback]
             │                  - RapidFuzz nearest match
             ▼                  - Bounded retry loop to LLM
     (Execute on DB)
```

---

## Project Structure

* **`config.py`**: Settings for Ollama endpoint, model name (`qwen3.5:9b`), Postgres credentials, and compiler parameters.
* **`catalog.py`**: Database schema metadata representation (tables, columns, primary/foreign keys, sample values) and live PostgreSQL introspection via `information_schema`.
* **`compiler.py`**: The core AST gatekeeper:
  * Tree parsing and traversal.
  * Destructive statement blocking.
  * Semantic catalog verification with `rapidfuzz` suggestions.
  * Deterministic AST rewriters (`GROUP BY`, `LIMIT`).
* **`generator.py`**: Local LLM interface connecting to Ollama, optimized for 100% GPU offload on an RTX 4060 (8GB VRAM).
* **`pipeline.py`**: End-to-end coordinator managing generation, AST compilation, and surgical repair loops.
* **`demo.py`**: Interactive and benchmark test suite.
* **`seed_postgres.py`** & **`seed_ecommerce.sql`**: Helper scripts to create and seed sample tables into your local PostgreSQL database.

---

## Quickstart

### 1. Run the Verification Demo
To see the AST Compiler, Auto-Patching, and Surgical Feedback in action:

```powershell
python demo.py
```

### 2. Run Interactive Mode
To test arbitrary natural language questions live against the compiler:

```powershell
python demo.py --interactive
```

### 3. Connect to your Local PostgreSQL Database (Optional)
To seed the sample e-commerce database in your local Postgres:

```powershell
# Set your postgres password if needed
$env:PGPASSWORD = "your_postgres_password"
python seed_postgres.py
```
