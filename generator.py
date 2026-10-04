import json
import urllib.request
import re
from typing import Optional, List, Dict
import config

SYSTEM_PROMPT = """You are NaturalSQL, a deterministic PostgreSQL generation engine.
Your task is to convert natural language requests into valid, executable PostgreSQL queries strictly conforming to the provided database schema.

RULES:
1. Output MUST be ONLY valid SQL code wrapped inside a single ```sql ... ``` markdown code block.
2. DO NOT write explanations, greetings, or commentary before or after the code block.
3. Use ONLY table and column names that exist in the provided schema. NEVER invent, assume, or hallucinate identifiers.
4. Adhere strictly to PostgreSQL syntax and conventions.
5. In ORDER BY and HAVING, you may reference aliases defined in the SELECT clause.
6. When joining tables, explicitly qualify columns with table names or short aliases (e.g. c.customer_id).
7. Use the explicit foreign key relationships defined in the schema for joins.
8. Only generate read-only SELECT queries. Never generate DROP, DELETE, INSERT, or UPDATE statements.
"""

class LLMGenerator:
    def __init__(self, host: str = config.OLLAMA_HOST, model: str = config.OLLAMA_MODEL):
        self.host = host.rstrip("/")
        self.model = model

    def _call_ollama(self, messages: List[Dict[str, str]], timeout: int = 60) -> str:
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.05,
                "top_p": 0.9,
                "num_ctx": 3072  # Optimal context for 100% GPU offload on RTX 4060
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                msg = result.get("message", {})
                content = msg.get("content", "").strip()
                # Fallback: if content is empty but model put output in thinking block
                if not content and msg.get("thinking"):
                    content = msg.get("thinking", "").strip()
                return content
        except Exception as e:
            raise RuntimeError(f"Failed to communicate with Ollama at {url}: {e}")

    def extract_sql(self, response_text: str) -> str:
        """Extracts SQL from ```sql ... ``` block or raw text, stripping thoughts."""
        if not response_text:
            return ""

        # 1. Strip any <think>...</think> reasoning tags
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", response_text, flags=re.IGNORECASE).strip()

        # 2. Extract ```sql ... ``` block
        match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()

        # 3. If no backticks, search for raw SELECT statement
        if "select" in cleaned.lower():
            sel_match = re.search(r"(SELECT\s+[\s\S]+)", cleaned, re.IGNORECASE)
            if sel_match:
                return sel_match.group(1).strip()

        return cleaned.strip()

    def generate(self, user_question: str, schema_text: str) -> str:
        """Generates initial SQL from natural language."""
        user_content = (
            f"DATABASE SCHEMA:\n\n{schema_text}\n\n"
            f"QUESTION: {user_question}\n\n"
            f"Write the PostgreSQL query that answers this question:"
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        raw_response = self._call_ollama(messages)
        return self.extract_sql(raw_response)

    def generate_repair(
        self,
        user_question: str,
        schema_text: str,
        failed_sql: str,
        surgical_feedback: str
    ) -> str:
        """
        Sends targeted compiler feedback back to the LLM in a fresh conversation turn.
        Avoids KV cache bloat and eliminates reasoning loops.
        """
        repair_content = (
            f"DATABASE SCHEMA:\n\n{schema_text}\n\n"
            f"QUESTION: {user_question}\n\n"
            f"Your previous query was rejected by the AST Compiler:\n"
            f"```sql\n{failed_sql}\n```\n\n"
            f"COMPILER ERROR FEEDBACK:\n{surgical_feedback}\n\n"
            f"INSTRUCTION:\n"
            f"Rewrite the SQL query to fix the exact error noted above. "
            f"Adhere strictly to the schema. Output ONLY valid SQL inside a ```sql ... ``` block."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": repair_content}
        ]

        raw_response = self._call_ollama(messages)
        return self.extract_sql(raw_response)
