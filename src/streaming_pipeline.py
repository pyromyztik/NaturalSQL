import time
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
import json

from src.core.catalog import DatabaseCatalog
from src.core.compiler import ASTCompiler, CompilationResult
from src.core.connections import execute_sql_query
from src.generator import LLMGenerator
from src import config

class StreamingPipeline:
    def __init__(
        self,
        catalog: DatabaseCatalog,
        dialect: str = "oracle",
        engine_url: Optional[str] = None,
        generator: Optional[LLMGenerator] = None,
        compiler: Optional[ASTCompiler] = None,
    ):
        self.catalog = catalog
        self.dialect = dialect
        self.engine_url = engine_url
        self.generator = generator or LLMGenerator()
        self.compiler = compiler or ASTCompiler(
            catalog=catalog,
            dialect=dialect,
            default_limit=config.DEFAULT_LIMIT
        )

    async def run_stream(
        self,
        question: str,
        execute: bool = True,
        max_retries: int = config.MAX_SURGICAL_RETRIES,
        failed_sql: Optional[str] = None,
        error_feedback: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        schema_text = self.catalog.to_prompt_schema(self.dialect)
        t_start = time.time()
        logs: List[str] = []

        def make_log(msg: str):
            logs.append(msg)
            return json.dumps({
                "type": "terminal_log",
                "line": msg,
                "timestamp": time.time()
            })

        yield json.dumps({
            "type": "pipeline_start",
            "question": question,
            "dialect": self.dialect,
            "model": self.generator.model,
            "is_retry": bool(error_feedback),
            "timestamp": time.time()
        })

        if error_feedback:
            yield make_log("=== [NaturalSQL Retry: Bundled Failure Context] ===")
            yield make_log(f"Question: \"{question}\"")
            yield make_log(f"Previous Error: {error_feedback}")
            if failed_sql:
                yield make_log(f"Failed SQL:\n{failed_sql}")
            if history:
                yield make_log(f"Context: {len(history)} recent interaction(s) bundled for reference")
            yield make_log(f"Target Database: {self.dialect.upper()} | Model: {self.generator.model}")
            yield make_log(f"\n[1/4] Querying LLM with repair context ({self.generator.model})...")
        else:
            yield make_log("=== [NaturalSQL Pipeline Initialized] ===")
            yield make_log(f"Question: \"{question}\"")
            if history:
                yield make_log(f"Context: {len(history)} recent interaction(s) bundled for reference")
            yield make_log(f"Target Database: {self.dialect.upper()} | Model: {self.generator.model}")
            yield make_log(f"Catalog Tables: {', '.join(self.catalog.table_names) if self.catalog.table_names else 'None (Empty Database)'}")
            yield make_log(f"\n[1/4] Querying LLM ({self.generator.model})...")

        yield json.dumps({
            "type": "step_start",
            "step": "generation",
            "title": "LLM Repair Generation" if error_feedback else "LLM Generation",
            "message": f"Prompting {self.generator.model} with error context..." if error_feedback else f"Prompting {self.generator.model}...",
            "timestamp": time.time()
        })

        t0 = time.time()
        stream_error = None

        loop = asyncio.get_running_loop()
        token_queue = asyncio.Queue()

        def stream_worker():
            try:
                if error_feedback and failed_sql:
                    gen = self.generator.generate_repair_stream(
                        user_question=question,
                        schema_text=schema_text,
                        failed_sql=failed_sql,
                        surgical_feedback=error_feedback,
                        history=history
                    )
                elif error_feedback:
                    augmented = f"{question}\n\n[Previous attempt failed with error: {error_feedback}. Please ensure the query resolves this.]"
                    gen = self.generator.generate_stream(user_question=augmented, schema_text=schema_text, history=history)
                else:
                    gen = self.generator.generate_stream(user_question=question, schema_text=schema_text, history=history)

                while True:
                    try:
                        token_item = next(gen)
                        loop.call_soon_threadsafe(token_queue.put_nowait, ("token", token_item))
                    except StopIteration as stop_err:
                        loop.call_soon_threadsafe(token_queue.put_nowait, ("done", stop_err.value))
                        break
            except Exception as e:
                loop.call_soon_threadsafe(token_queue.put_nowait, ("error", str(e)))

        worker_thread = asyncio.create_task(asyncio.to_thread(stream_worker))

        payload = None
        while True:
            msg_type, val = await token_queue.get()
            if msg_type == "token":
                yield json.dumps({
                    "type": "terminal_token",
                    "token": val.get("token", ""),
                    "token_type": val.get("type", "content")
                })
            elif msg_type == "done":
                payload = val
                break
            elif msg_type == "error":
                stream_error = val
                break

        await worker_thread

        if stream_error:
            err_msg = f"[Error] Failed to communicate with LLM: {stream_error}"
            yield make_log(err_msg)
            yield json.dumps({
                "type": "error",
                "step": "generation",
                "message": err_msg
            })
            return

        gen_duration = round((time.time() - t0) * 1000)
        parsed_res = payload if isinstance(payload, dict) else self.generator.parse_response(str(payload))

        if parsed_res.get("type") == "conversational":
            conv_text = parsed_res.get("text", "")
            yield make_log(f"[NaturalSQL] Prompt does not require database querying. Responding directly.")
            yield make_log(f"--- Direct Response ---\n{conv_text}\n-----------------------")

            yield json.dumps({
                "type": "direct_response",
                "text": conv_text,
                "duration_ms": gen_duration,
                "timestamp": time.time()
            })

            yield json.dumps({
                "type": "pipeline_complete",
                "status": "done",
                "is_conversational": True,
                "response_text": conv_text,
                "initial_sql": "",
                "final_sql": "",
                "attempts": 1,
                "patches_applied": [],
                "healer_iterations": [],
                "execution": None,
                "total_duration_ms": round((time.time() - t_start) * 1000),
                "logs": logs
            })
            return

        current_sql = parsed_res.get("sql", "")
        initial_sql = current_sql

        yield make_log(f"[LLM] Initial SQL generation completed ({gen_duration}ms)")
        yield make_log(f"--- Raw SQL Output ---\n{initial_sql}\n----------------------")

        yield json.dumps({
            "type": "generation_complete",
            "step": "generation",
            "sql": initial_sql,
            "duration_ms": gen_duration,
            "timestamp": time.time()
        })

        # Step 2: AST Validation & Healer Loop
        attempts = 1
        compilation: Optional[CompilationResult] = None
        all_feedbacks = []
        healer_iterations = []

        yield make_log(f"\n[2/4] AST Compiler: parsing and validating attempt #{attempts}...")
        yield json.dumps({
            "type": "step_start",
            "step": "gatekeeper",
            "title": "AST Compiler Validation",
            "message": "Parsing SQL AST and validating catalog identifiers...",
            "timestamp": time.time()
        })

        while attempts <= (1 + max_retries):
            t_check = time.time()
            compilation = await asyncio.to_thread(self.compiler.compile, current_sql)
            check_duration = round((time.time() - t_check) * 1000)

            if compilation.is_valid:
                yield make_log(f"[AST Compiler] Validation PASSED on attempt #{attempts} ({check_duration}ms)")
                if compilation.patches:
                    yield make_log(f"\n[3/4] AST Auto-Patches applied:")
                    for p in compilation.patches:
                        yield make_log(f"  * {p}")
                else:
                    yield make_log(f"\n[3/4] AST Auto-Patches: None required.")

                yield json.dumps({
                    "type": "compiler_pass",
                    "step": "gatekeeper",
                    "attempt": attempts,
                    "patches": compilation.patches,
                    "duration_ms": check_duration,
                    "timestamp": time.time()
                })
                break

            feedback = compilation.surgical_feedback or "\n".join(compilation.errors)
            all_feedbacks.append(feedback)

            yield make_log(f"[AST Compiler] FAILED catalog check on attempt #{attempts}:")
            for err in compilation.errors:
                yield make_log(f"  ! {err}")

            healer_iter = {
                "iteration": attempts,
                "rejected_sql": current_sql,
                "errors": compilation.errors,
                "surgical_feedback": feedback
            }
            healer_iterations.append(healer_iter)

            yield json.dumps({
                "type": "surgical_feedback",
                "step": "gatekeeper",
                "attempt": attempts,
                "rejected_sql": current_sql,
                "errors": compilation.errors,
                "surgical_feedback": feedback,
                "timestamp": time.time()
            })

            if attempts > max_retries:
                yield make_log(f"[AST Healer] Maximum surgical retries ({max_retries}) exceeded.")
                yield json.dumps({
                    "type": "healer_exhausted",
                    "step": "gatekeeper",
                    "max_retries": max_retries,
                    "message": "Maximum surgical retries exceeded."
                })
                break

            # Surgical repair turn
            yield make_log(f"\n[Healer] Dispatching surgical error feedback to LLM for targeted repair (Attempt {attempts + 1})...")
            yield json.dumps({
                "type": "step_start",
                "step": "healer_repair",
                "attempt": attempts,
                "title": f"Surgical Repair #{attempts}",
                "message": f"LLM correcting query (Attempt #{attempts + 1})...",
                "timestamp": time.time()
            })

            t_rep = time.time()
            repair_queue = asyncio.Queue()
            rep_error = None

            def repair_worker():
                try:
                    rep_gen = self.generator.generate_repair_stream(
                        user_question=question,
                        schema_text=schema_text,
                        failed_sql=current_sql,
                        surgical_feedback=feedback
                    )
                    while True:
                        try:
                            token_item = next(rep_gen)
                            loop.call_soon_threadsafe(repair_queue.put_nowait, ("token", token_item))
                        except StopIteration as stop_err:
                            loop.call_soon_threadsafe(repair_queue.put_nowait, ("done", stop_err.value))
                            break
                except Exception as e:
                    loop.call_soon_threadsafe(repair_queue.put_nowait, ("error", str(e)))

            rep_thread = asyncio.create_task(asyncio.to_thread(repair_worker))

            while True:
                msg_type, rep_val = await repair_queue.get()
                if msg_type == "token":
                    yield json.dumps({
                        "type": "terminal_token",
                        "token": rep_val.get("token", ""),
                        "token_type": rep_val.get("type", "content")
                    })
                elif msg_type == "done":
                    current_sql = rep_val
                    break
                elif msg_type == "error":
                    rep_error = rep_val
                    break

            await rep_thread

            if rep_error:
                err_msg = f"[Error] Surgical repair call failed: {rep_error}"
                yield make_log(err_msg)
                yield json.dumps({
                    "type": "error",
                    "step": "healer_repair",
                    "message": err_msg
                })
                return

            rep_duration = round((time.time() - t_rep) * 1000)
            yield make_log(f"[LLM] Repaired SQL received ({rep_duration}ms):")
            yield make_log(f"{current_sql}")

            yield json.dumps({
                "type": "repair_received",
                "step": "healer_repair",
                "attempt": attempts,
                "sql": current_sql,
                "duration_ms": rep_duration,
                "timestamp": time.time()
            })

            attempts += 1

        if not compilation or not compilation.is_valid:
            yield make_log(f"\n[Fatal] Failed to compile a valid SQL query within retry limits.")
            yield json.dumps({
                "type": "pipeline_failed",
                "question": question,
                "initial_sql": initial_sql,
                "attempts": attempts,
                "surgical_feedbacks": all_feedbacks,
                "healer_iterations": healer_iterations,
                "logs": logs,
                "error": "Failed to compile a valid, schema-compliant query.",
                "total_duration_ms": round((time.time() - t_start) * 1000)
            })
            return

        final_sql = compilation.compiled_sql or current_sql
        patches_applied = compilation.patches
        is_mutation = compilation.is_mutation
        mutation_type = compilation.mutation_type

        yield make_log(f"\n--- Final Clean & Verified SQL ---\n{final_sql}\n----------------------------------")

        yield json.dumps({
            "type": "query_verified",
            "final_sql": final_sql,
            "patches_applied": patches_applied,
            "attempts": attempts,
            "healer_iterations": healer_iterations,
            "is_mutation": is_mutation,
            "mutation_type": mutation_type,
            "timestamp": time.time()
        })

        # Step 4: Safety Check vs Execution
        # If this statement modifies or mutates data: PAUSE and request explicit approval!
        if is_mutation:
            yield make_log(f"\n⚠️  [Safety Gatekeeper] Query contains data modifications ({mutation_type}).")
            yield make_log(f"⚠️  [Safety Gatekeeper] Execution suspended. User approval is required before applying this change.")

            yield json.dumps({
                "type": "approval_required",
                "final_sql": final_sql,
                "is_mutation": True,
                "mutation_type": mutation_type,
                "message": f"This statement performs a {mutation_type} operation on the active database.",
                "timestamp": time.time()
            })

            total_duration = round((time.time() - t_start) * 1000)
            yield make_log(f"\n=== [Pipeline Suspended for Approval: {total_duration}ms] ===")

            yield json.dumps({
                "type": "pipeline_complete",
                "success": True,
                "status": "approval_required",
                "question": question,
                "initial_sql": initial_sql,
                "final_sql": final_sql,
                "attempts": attempts,
                "patches_applied": patches_applied,
                "healer_iterations": healer_iterations,
                "logs": logs,
                "is_mutation": True,
                "mutation_type": mutation_type,
                "execution": None,
                "total_duration_ms": total_duration,
                "timestamp": time.time()
            })
            return

        # Pure read query (SELECT)
        exec_result = None
        if execute and self.engine_url:
            yield make_log(f"\n[4/4] Executing query on {self.dialect.upper()} database...")
            yield json.dumps({
                "type": "step_start",
                "step": "execution",
                "title": "Database Execution",
                "message": f"Executing on {self.dialect.upper()}...",
                "timestamp": time.time()
            })

            exec_result = await asyncio.to_thread(execute_sql_query, self.engine_url, final_sql, False)
            exec_duration = exec_result.get("duration_ms", 0)

            if not exec_result.get("success"):
                yield make_log(f"[Database Error] {exec_result.get('error')} ({exec_duration}ms)")
            else:
                row_count = exec_result.get("row_count", 0)
                yield make_log(f"[Database] Success: {row_count} row(s) returned ({exec_duration}ms).")

        total_duration = round((time.time() - t_start) * 1000)
        yield make_log(f"\n=== [Pipeline Complete: {total_duration}ms] ===")

        yield json.dumps({
            "type": "pipeline_complete",
            "success": True,
            "status": "done",
            "question": question,
            "initial_sql": initial_sql,
            "final_sql": final_sql,
            "attempts": attempts,
            "patches_applied": patches_applied,
            "healer_iterations": healer_iterations,
            "logs": logs,
            "is_mutation": False,
            "execution": exec_result,
            "total_duration_ms": total_duration,
            "timestamp": time.time()
        })
