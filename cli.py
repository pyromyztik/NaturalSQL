#!/usr/bin/env python3
"""
NaturalSQL CLI: Universal Database Assistant & Safety Gatekeeper.
Supports Oracle, PostgreSQL, MySQL, and SQLite.
"""
import sys
import os
import argparse
import time
from typing import Optional, List, Dict, Any

# Ensure Windows terminal doesn't crash on utf-8 characters
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.core.catalog import DatabaseCatalog
from src.core.compiler import ASTCompiler, CompilationResult
from src.core.connections import (
    ConnectionRegistry,
    parse_connection_input,
    test_connection,
    introspect_connection,
    execute_sql_query
)
from src.generator import LLMGenerator

BANNER = r"""
========================================================================
    __  ______  ________  ______  ___    __     _____ ____    __ 
   / | / /   | /_  __/ / / / __ \/   |  / /    / ___// __ \  / / 
  /  |/ / /| |  / / / / / / /_/ / /| | / /     \__ \/ / / / / /  
 / /|  / ___ | / / / /_/ / _, _/ ___ |/ /___  ___/ / /_/ / / /___
/_/ |_/_/  |_|/_/  \____/_/ |_/_/  |_/_____/ /____/\___\_\/_____/

                      NATURALSQL CLI v2.0
========================================================================
"""

def render_ascii_table(columns: List[str], rows: List[Dict[str, Any]], max_col_width: int = 35) -> str:
    """Renders tabular data into a clean formatted ASCII table."""
    if not columns or not rows:
        return "(0 rows returned)"

    # Compute column widths
    widths = {}
    for col in columns:
        widths[col] = len(str(col))

    for row in rows:
        for col in columns:
            val_str = str(row.get(col, ""))
            if len(val_str) > max_col_width:
                val_str = val_str[:max_col_width - 3] + "..."
            widths[col] = max(widths[col], len(val_str))

    # Build border and header
    header_line = " | ".join(str(col).ljust(widths[col]) for col in columns)
    sep_line = "-+-".join("-" * widths[col] for col in columns)

    row_lines = []
    for row in rows:
        r_line = []
        for col in columns:
            val_str = str(row.get(col, ""))
            if len(val_str) > max_col_width:
                val_str = val_str[:max_col_width - 3] + "..."
            r_line.append(val_str.ljust(widths[col]))
        row_lines.append(" | ".join(r_line))

    return f"\n{header_line}\n{sep_line}\n" + "\n".join(row_lines) + f"\n({len(rows)} row(s))\n"

def process_query(
    question: str,
    catalog: DatabaseCatalog,
    dialect: str,
    engine_url: str,
    generator: LLMGenerator,
    compiler: ASTCompiler
) -> bool:
    """Generates, verifies, and executes a natural language query with mutation approval."""
    schema_text = catalog.to_prompt_schema(dialect)

    print(f"\n[1/3] Generating SQL via local LLM ({generator.model})...")
    t0 = time.time()
    gen = generator.generate_stream(user_question=question, schema_text=schema_text)
    
    # Stream tokens live to console
    full_output = ""
    try:
        while True:
            chunk = next(gen)
            if chunk.get("type") == "content":
                tok = chunk.get("token", "")
                sys.stdout.write(tok)
                sys.stdout.flush()
    except StopIteration as e:
        parsed_res = e.value

    print() # newline
    gen_duration = round((time.time() - t0) * 1000)

    if parsed_res.get("type") == "conversational":
        print(f"\n[Assistant]: {parsed_res.get('text', '')}\n")
        return True

    candidate_sql = parsed_res.get("sql", "").strip()
    if not candidate_sql:
        print("[Error] No SQL query generated.")
        return False

    print(f"\n[2/3] AST Compiler: validating {dialect.upper()} query...")
    compilation: CompilationResult = compiler.compile(candidate_sql)

    # Healer retry if invalid
    retries = 0
    max_retries = 2
    while not compilation.is_valid and retries < max_retries:
        retries += 1
        feedback = compilation.surgical_feedback or "\n".join(compilation.errors)
        print(f"  ! Validation failed on attempt #{retries}: {feedback}")
        print(f"  -> Dispatched surgical feedback to LLM for targeted repair (Attempt #{retries + 1})...")

        candidate_sql = generator.generate_repair(
            user_question=question,
            schema_text=schema_text,
            failed_sql=candidate_sql,
            surgical_feedback=feedback
        )
        compilation = compiler.compile(candidate_sql)

    if not compilation.is_valid:
        print(f"\n[Fatal Error] Query compilation failed after {retries} retries:")
        for err in compilation.errors:
            print(f"  - {err}")
        return False

    final_sql = compilation.compiled_sql or candidate_sql
    print(f"\n--- Verified SQL Query ({dialect.upper()}) ---")
    print(final_sql)
    print("------------------------------------------")

    # Safety Gatekeeper Check for Mutations
    if compilation.is_mutation:
        print(f"\n[!] [SAFETY GATEKEEPER] Mutation detected: {compilation.mutation_type}")
        print(f"This statement will INSERT, UPDATE, DELETE, or alter schema in the connected database.")
        
        try:
            confirm = input(f"Approve execution of this statement on database? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return False

        if confirm not in ["y", "yes"]:
            print("Operation cancelled by user. No data was modified.\n")
            return False

        print("\n[3/3] Executing approved mutation...")
        res = execute_sql_query(engine_url, final_sql, is_mutation=True)
        if res.get("success"):
            print(f"[OK] Success: {res.get('rows_affected', 0)} row(s) affected ({res.get('duration_ms')}ms).\n")
        else:
            print(f"[ERROR] Execution Error: {res.get('error')}\n")
        return True

    # Read-only SELECT query
    print(f"\n[3/3] Executing query on {dialect.upper()}...")
    res = execute_sql_query(engine_url, final_sql, is_mutation=False)
    if not res.get("success"):
        print(f"[ERROR] Database Error: {res.get('error')}\n")
        return False

    table_output = render_ascii_table(res.get("columns", []), res.get("rows", []))
    print(table_output)
    print(f"Query returned in {res.get('duration_ms')}ms.\n")
    return True

def connect_database_prompt(registry: ConnectionRegistry) -> tuple:
    """Interactively prompts user to select or connect a database."""
    saved = registry.load()
    
    if saved:
        print("Saved Database Connections:")
        conn_keys = list(saved.keys())
        for idx, key in enumerate(conn_keys, 1):
            info = saved[key]
            print(f"  [{idx}] {info.get('name')} ({info.get('dialect').upper()} - {info.get('display_url')})")
        print(f"  [{len(conn_keys) + 1}] Connect New Database...")
        print(f"  [0] Forget All Saved Databases")

        while True:
            choice = input(f"\nSelect a connection [1-{len(conn_keys) + 1}]: ").strip()
            if choice == "0":
                registry.clear_all()
                print("All saved database connections have been forgotten.\n")
                return connect_database_prompt(registry)
            if choice.isdigit():
                val = int(choice)
                if 1 <= val <= len(conn_keys):
                    sel_meta = saved[conn_keys[val - 1]]
                    print(f"\nConnecting to '{sel_meta.get('name')}'...")
                    cat, dialect = introspect_connection(sel_meta["engine_url"])
                    return sel_meta["engine_url"], dialect, cat, sel_meta.get("name")
                elif val == len(conn_keys) + 1:
                    break

    # Prompt for connection URI
    print("\nSupported Standard Connection Formats:")
    print("  - PostgreSQL : postgresql://user:password@localhost:5432/dbname")
    print("  - Oracle     : oracle://user:password@localhost:1521/FREEPDB1")
    print("               : or terminal EZConnect: user/password@localhost:1521/FREEPDB1")
    print("  - MySQL      : mysql://user:password@localhost:3306/dbname")

    while True:
        raw = input("\nEnter Database Connection URI or Link: ").strip()
        if not raw:
            continue
        try:
            parsed = parse_connection_input(raw)
            print(f"Testing connection to {parsed['dialect'].upper()} ({parsed['display_url']})...")
            test_res = test_connection(raw)
            if not test_res.get("success"):
                print(f"[ERROR] Connection failed: {test_res.get('error')}")
                continue

            name = input("Enter a friendly name for this DB (optional): ").strip()
            if not name:
                name = f"{parsed['dialect'].title()} Database"

            saved_entry = registry.add(name=name, raw_connection=raw)
            cat, dialect = introspect_connection(saved_entry["engine_url"])
            print(f"[OK] Successfully connected to '{name}' ({dialect.upper()})! Introspected {len(cat.table_names)} table(s).\n")
            return saved_entry["engine_url"], dialect, cat, name
        except Exception as e:
            print(f"[ERROR] Invalid connection input: {e}")

def main():
    parser = argparse.ArgumentParser(description="NaturalSQL Universal CLI & Safety Gatekeeper")
    parser.add_argument("--conn", "-c", type=str, help="Database Connection URI (e.g. postgresql://..., oracle://...)")
    parser.add_argument("--query", "-q", type=str, help="Natural language question to execute in one-shot mode")
    parser.add_argument("--forget", action="store_true", help="Forget all saved database connections and exit")
    parser.add_argument("--list", "-l", action="store_true", help="List saved database connections")
    args = parser.parse_args()

    registry = ConnectionRegistry()

    if args.forget:
        registry.clear_all()
        print("[OK] All saved database connections have been forgotten.")
        sys.exit(0)

    if args.list:
        saved = registry.load()
        if not saved:
            print("No database connections saved.")
        else:
            print(f"Saved Databases ({len(saved)}):")
            for cid, meta in saved.items():
                print(f"  - {meta.get('name')} [{meta.get('dialect').upper()}] : {meta.get('display_url')}")
        sys.exit(0)

    # 1. Establish database connection
    engine_url = None
    dialect = None
    catalog = None
    db_name = None

    if args.conn:
        try:
            parsed = parse_connection_input(args.conn)
            cat, d_name = introspect_connection(parsed["engine_url"])
            engine_url = parsed["engine_url"]
            dialect = d_name
            catalog = cat
            db_name = f"{dialect.title()} DB"
        except Exception as e:
            print(f"❌ Failed to connect to specified connection '{args.conn}': {e}")
            sys.exit(1)
    else:
        print(BANNER)
        engine_url, dialect, catalog, db_name = connect_database_prompt(registry)

    generator = LLMGenerator()
    compiler = ASTCompiler(catalog=catalog, dialect=dialect)

    # 2. One-shot query mode
    if args.query:
        print(f"\nDatabase: {db_name} ({dialect.upper()}) | Tables: {', '.join(catalog.table_names)}")
        print(f"Question: \"{args.query}\"")
        success = process_query(args.query, catalog, dialect, engine_url, generator, compiler)
        sys.exit(0 if success else 1)

    # 3. Interactive REPL Mode
    print(f"\n=== NaturalSQL Interactive Shell ({db_name}) ===")
    print(f"Connected to {dialect.upper()} with {len(catalog.table_names)} tables: {', '.join(catalog.table_names)}")
    print("Type your questions in natural English. Commands: /connect, /tables, /forget, /exit\n")

    while True:
        try:
            prompt_str = f"NaturalSQL ({dialect.lower()})> "
            user_input = input(prompt_str).strip()
            if not user_input:
                continue

            # Special CLI Commands
            if user_input in ["/exit", "exit", "quit", ":q"]:
                print("Goodbye!")
                break
            elif user_input == "/tables":
                print(f"\nCatalog Tables ({len(catalog.table_names)}):")
                for t in catalog.table_names:
                    tbl = catalog.get_table(t)
                    cols = [c.name for c in tbl.columns.values()]
                    print(f"  - {t}: {', '.join(cols)}")
                print()
                continue
            elif user_input.startswith("/connect"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    raw_new = parts[1].strip()
                    try:
                        parsed_new = parse_connection_input(raw_new)
                        cat_new, d_new = introspect_connection(parsed_new["engine_url"])
                        engine_url = parsed_new["engine_url"]
                        dialect = d_new
                        catalog = cat_new
                        compiler = ASTCompiler(catalog=catalog, dialect=dialect)
                        db_name = f"{dialect.title()} DB"
                        print(f"Switched connection to {dialect.upper()} ({len(catalog.table_names)} tables).\n")
                    except Exception as e:
                        print(f"Failed to connect: {e}\n")
                else:
                    engine_url, dialect, catalog, db_name = connect_database_prompt(registry)
                    compiler = ASTCompiler(catalog=catalog, dialect=dialect)
                continue
            elif user_input == "/forget":
                registry.clear_all()
                print("All saved database connections have been forgotten.\n")
                engine_url, dialect, catalog, db_name = connect_database_prompt(registry)
                compiler = ASTCompiler(catalog=catalog, dialect=dialect)
                continue
            elif user_input == "/help":
                print("\nAvailable Commands:")
                print("  /connect [uri]  : Connect to or switch database")
                print("  /tables         : List introspected tables and columns")
                print("  /forget         : Forget all saved database connections")
                print("  /exit, exit     : Exit NaturalSQL CLI\n")
                continue

            # Process English Text-to-SQL Question
            process_query(user_input, catalog, dialect, engine_url, generator, compiler)

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()
