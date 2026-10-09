# NaturalSQL: Compiler-Style Text-to-SQL Gatekeeper

A deterministic safety, verification, and repair pipeline between an LLM and databases (PostgreSQL & SQLite).

Instead of executing raw LLM-generated SQL directly on your database, **NaturalSQL** parses the query into an **Abstract Syntax Tree (AST)** using `sqlglot`, validates it against the schema catalog, auto-patches common model omissions (missing `GROUP BY` projections, safety `LIMIT`s), and executes bounded surgical feedback loops for hallucinated identifiers.

---

## Clean Project Structure

```
NaturalSQL/
├── src/                               # Core Python package (PostgreSQL & AST Engine)
│   ├── core/
│   │   ├── compiler.py               # AST Compiler Gatekeeper & Auto-Patchers
│   │   ├── catalog.py                # Schema metadata & PostgreSQL introspection
│   │   └── sqlite_catalog.py         # SQLite schema introspection
│   ├── generator.py                  # Ollama connector with retry & token bounding
│   ├── pipeline.py                   # End-to-end orchestration & surgical repair loop
│   ├── config.py                     # Core application configuration
│   └── __init__.py                   # Package exports
├── benchmark/                         # Fully isolated benchmark suite
│   ├── config.py                     # Benchmark-specific settings & timeouts
│   ├── executor.py                   # Read-only SQLite runner with 5s query watchdog
│   ├── checkpoint.py                 # Atomic checkpoint manager (crash & resume support)
│   ├── reporter.py                   # Live ETA progress, Markdown & JSON reports
│   ├── runner.py                     # Benchmark execution engine & signal handler
│   ├── run.py                        # Standalone benchmark CLI entry point
│   ├── fixtures/                     # Datasets & SQLite database fixtures
│   │   ├── concert_singer.sqlite     # Spider SQLite database fixture
│   │   ├── spider_dev_sample.json    # 45 concert_singer dev queries
│   │   └── spider_dev_full.json      # All 1,034 Spider dev queries
│   └── results/                      # Auto-generated (git-ignored) run artifacts
│       ├── checkpoints/              # Resumable run checkpoints
│       ├── reports/                  # Detailed Markdown summaries
│       └── data/                     # Complete execution metric JSON dumps
├── db/                                # PostgreSQL utilities
│   ├── seed_postgres.py              # Live PostgreSQL seeder
│   └── seed_ecommerce.sql            # Sample e-commerce store dataset
├── demo.py                            # Interactive & scenario demonstration CLI
├── run_benchmark.py                   # Lightweight convenience runner
├── Modelfile                          # Tuned Ollama Modelfile for naturalsql model
└── README.md
```

---

## Quickstart

### 1. Run the Interactive Demo
```powershell
# Run the 3 pre-built scenarios
python demo.py

# Or run interactive CLI where you can type arbitrary English questions
python demo.py --interactive
```

### 2. Run the Resilient Spider Benchmark
Compare the **Baseline Naive LLM** against the **NaturalSQL Gatekeeper** on Spider validation queries:

```powershell
# Run the benchmark (supports automatic resuming from checkpoints)
python benchmark/run.py --samples 45

# Start fresh (ignores and clears prior checkpoints)
python benchmark/run.py --samples 45 --fresh

# Resume from query 26 through 45
python benchmark/run.py --offset 25 --samples 20
```

*Results, checkpoints, and Markdown reports are automatically saved under `benchmark/results/`.*
```

---

## Benchmark Metrics Reported

1. **Valid SQL Rate (Executability)**: Percentage of queries that parse and execute on the database without engine errors.
2. **Execution Accuracy (EX)**: Matches the returned data tuples against human-written gold ground-truth queries.
3. **Execution Accuracy by Difficulty**: Breaks down results across **Easy**, **Medium**, **Hard**, and **Extra Hard** tiers.
4. **Latency Tracking**: Average latency per query (seconds) and total benchmark execution time.
5. **Zero-Token Auto-Patches**: Total count of queries salvaged deterministically by the compiler without making an LLM API call.
