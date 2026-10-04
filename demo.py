import sys
import time
from catalog import DatabaseCatalog
from compiler import ASTCompiler
from generator import LLMGenerator
from pipeline import TextToSQLPipeline
import config

def print_banner(text: str):
    print("\n" + "=" * 70, flush=True)
    print(f"  {text}", flush=True)
    print("=" * 70, flush=True)

def run_demonstration():
    print_banner("NATURAL SQL: AST COMPILER & REPAIR GATEKEEPER")
    print(f"Model: {config.OLLAMA_MODEL} (Local via Ollama)")
    print(f"Dialect: PostgreSQL")
    print(f"Catalog: E-Commerce Store (customers, products, orders, order_items)")

    catalog = DatabaseCatalog.create_sample_ecommerce()
    generator = LLMGenerator()
    compiler = ASTCompiler(catalog=catalog, dialect="postgres", default_limit=50)
    pipeline = TextToSQLPipeline(catalog=catalog, generator=generator, compiler=compiler)

    test_queries = [
        {
            "title": "Scenario 1: Aggregation & Auto-Patch (Missing GROUP BY / LIMIT)",
            "question": "Show the number of customers in each city, sorted from highest to lowest."
        },
        {
            "title": "Scenario 2: Multi-Table Join & Filtering",
            "question": "List all customers who have placed an order with status 'delivered' and their total amount spent."
        },
        {
            "title": "Scenario 3: Hallucination & Surgical Feedback Test",
            "question": "Get customer full name, user_mail, and their account creation date."
        }
    ]

    for test in test_queries:
        print_banner(test["title"])
        print(f"User Prompt: \"{test['question']}\"")
        print("\n[Pipeline] Asking local LLM...")

        t0 = time.time()
        result = pipeline.run(test["question"], execute=False)
        duration = time.time() - t0

        print(f"[Pipeline] Finished in {duration:.2f}s across {result.attempts} attempt(s)")

        print("\n--- 1. Raw LLM Generation ---")
        print(result.initial_sql)

        if result.surgical_feedbacks:
            print("\n--- 2. Compiler Surgical Feedback (LLM Hallucination Detected) ---")
            for idx, fb in enumerate(result.surgical_feedbacks, 1):
                print(f"[Feedback Iteration {idx}]:\n{fb}")

        if result.patches_applied:
            print("\n--- 3. Rule-Based AST Auto-Patches Applied (0 Extra Tokens) ---")
            for patch in result.patches_applied:
                print(f"  * {patch}")

        print("\n--- 4. Final Clean & Verified PostgreSQL ---")
        print(result.compiled_sql)

        if not result.success:
            print(f"\n[Warning] Compilation failed: {result.execution_error}")

def interactive_mode():
    catalog = DatabaseCatalog.create_sample_ecommerce()
    generator = LLMGenerator()
    compiler = ASTCompiler(catalog=catalog, dialect="postgres", default_limit=50)
    pipeline = TextToSQLPipeline(catalog=catalog, generator=generator, compiler=compiler)

    print_banner("INTERACTIVE TEXT-TO-SQL COMPILER MODE")
    print("Type your questions in natural English (e.g. 'Which products are low on stock?')")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            q = input("\nEnter Question > ").strip()
            if not q:
                continue
            if q.lower() in ("exit", "quit", "q"):
                break

            print("\nCompiling query...")
            res = pipeline.run(q, execute=False)

            if res.surgical_feedbacks:
                print("\n[Surgical Feedback Sent to LLM]:")
                for fb in res.surgical_feedbacks:
                    print(fb)

            if res.patches_applied:
                print("\n[AST Patches Applied (0 Tokens)]:")
                for p in res.patches_applied:
                    print(f"  * {p}")

            print("\n[Compiled PostgreSQL]:")
            print(res.compiled_sql)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        run_demonstration()
