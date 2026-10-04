from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from catalog import DatabaseCatalog
from compiler import ASTCompiler, CompilationResult
from generator import LLMGenerator
import config

@dataclass
class PipelineResult:
    success: bool
    question: str
    initial_sql: str
    compiled_sql: str
    attempts: int
    patches_applied: List[str] = field(default_factory=list)
    surgical_feedbacks: List[str] = field(default_factory=list)
    rows: Optional[List[Dict[str, Any]]] = None
    execution_error: Optional[str] = None

class TextToSQLPipeline:
    """
    End-to-end pipeline:
    User Question -> Local LLM -> AST Compiler (Catalog Check & Auto-Patch) -> (Surgical Retry if needed) -> Safe Execution
    """
    def __init__(
        self,
        catalog: DatabaseCatalog,
        generator: Optional[LLMGenerator] = None,
        compiler: Optional[ASTCompiler] = None,
        db_connection_params: Optional[dict] = None
    ):
        self.catalog = catalog
        self.generator = generator or LLMGenerator()
        self.compiler = compiler or ASTCompiler(catalog=catalog, dialect="postgres", default_limit=config.DEFAULT_LIMIT)
        self.db_params = db_connection_params

    def run(self, question: str, execute: bool = False, max_retries: int = config.MAX_SURGICAL_RETRIES) -> PipelineResult:
        schema_text = self.catalog.to_prompt_schema()
        
        # 1. Initial Generation
        print(f"  -> Sending question to local LLM ({self.generator.model})...", flush=True)
        current_sql = self.generator.generate(user_question=question, schema_text=schema_text)
        initial_sql = current_sql
        
        attempts = 1
        all_surgical_feedbacks = []
        compilation: Optional[CompilationResult] = None

        # 2. Gatekeeper Loop
        while attempts <= (1 + max_retries):
            print(f"  -> AST Compiler: parsing and validating attempt #{attempts}...", flush=True)
            compilation = self.compiler.compile(current_sql)

            if compilation.is_valid:
                print(f"  -> AST Compiler: PASSED! (Patches applied: {len(compilation.patches)})", flush=True)
                break

            # If invalid, record feedback
            feedback = compilation.surgical_feedback or "\n".join(compilation.errors)
            all_surgical_feedbacks.append(feedback)
            print(f"  -> AST Compiler: FAILED catalog check. Generating surgical feedback...", flush=True)

            if attempts > max_retries:
                print(f"  -> Max surgical retries exceeded.", flush=True)
                break

            # Surgical repair call back to the LLM
            print(f"  -> Sending surgical feedback back to LLM for targeted fix...", flush=True)
            current_sql = self.generator.generate_repair(
                user_question=question,
                schema_text=schema_text,
                failed_sql=current_sql,
                surgical_feedback=feedback
            )
            attempts += 1

        if not compilation or not compilation.is_valid:
            return PipelineResult(
                success=False,
                question=question,
                initial_sql=initial_sql,
                compiled_sql=current_sql,
                attempts=attempts,
                surgical_feedbacks=all_surgical_feedbacks,
                execution_error="Failed to compile a valid SQL query within retry limit."
            )

        # 3. Safe Execution (Optional)
        rows = None
        exec_error = None
        if execute and self.db_params:
            try:
                conn = psycopg2.connect(**self.db_params)
                # Enforce read-only transaction mode at the database level as well
                conn.set_session(readonly=True, autocommit=True)
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(compilation.compiled_sql)
                    rows = cur.fetchall()
                conn.close()
            except Exception as e:
                exec_error = f"Database runtime error: {str(e)}"

        return PipelineResult(
            success=True,
            question=question,
            initial_sql=initial_sql,
            compiled_sql=compilation.compiled_sql,
            attempts=attempts,
            patches_applied=compilation.patches,
            surgical_feedbacks=all_surgical_feedbacks,
            rows=rows,
            execution_error=exec_error
        )
