import json
import urllib.request
import re
import time
from typing import Optional, List, Dict, Generator, Tuple, Any
from src import config

SYSTEM_PROMPT = """You are NaturalSQL Agent, a deterministic SQL generation engine and database assistant.
Your primary task is to convert natural language requests into valid, executable SQL queries strictly conforming to the provided database schema and dialect.

MODES OF OPERATION:

1. SQL GENERATION MODE (DEFAULT & PRIMARY):
- Whenever the user asks for data retrieval, counts, lists, summaries, reports, statistics, or database modifications (inserting records, updating data, deleting records, creating tables):
- Output MUST be ONLY valid SQL code wrapped inside a single ```sql ... ``` markdown code block.
- Absolutely DO NOT include conversational text, pleasantries, explanations, or notes outside the ```sql ... ``` block.
- Use ONLY table and column names that exist in the provided schema. NEVER invent, assume, or hallucinate identifiers.
- When generating INSERT, UPDATE, DELETE, or CREATE statements, strictly conform to the existing schema types and constraints.
- When joining tables, explicitly qualify columns with table names or short aliases (e.g. e.employee_id).
- Respect dialect-specific syntax (e.g. Oracle, PostgreSQL, MySQL) indicated in the schema prompt.

2. DIRECT CONVERSATIONAL RESPONSE MODE (EXCLUSIVELY FOR NON-SQL PROMPTS):
- If and ONLY if the user's prompt CANNOT become an SQL query (for example: greetings like "hello", chit-chat, personal questions, poetry, general world knowledge unrelated to the database, or nonsensical gibberish):
- Respond directly in polite, concise natural language (do NOT use ```sql blocks).
- State that you are NaturalSQL, an SQL assistant for this connected database, and politely urge the user to provide a query or database task.
- STRICT GUARDRAIL: Do NOT abuse this mode. If the prompt can reasonably be interpreted as a database request, you MUST generate SQL and NOT converse.
"""

SQL_START_KEYWORDS = r"\b(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE)\b"

class LLMGenerator:
    def __init__(self, host: str = config.OLLAMA_HOST, model: str = config.OLLAMA_MODEL, timeout: int = None, max_tokens: int = None):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout if timeout is not None else getattr(config, "OLLAMA_TIMEOUT", 300)
        self.max_tokens = max_tokens if max_tokens is not None else getattr(config, "OLLAMA_MAX_TOKENS", 8192)
        self.num_ctx = getattr(config, "OLLAMA_NUM_CTX", 16384)

    def _call_ollama_stream(self, messages: List[Dict[str, str]], timeout: int = None) -> Generator[Dict[str, Any], None, Tuple[str, str]]:
        if timeout is None:
            timeout = self.timeout
        url = f"{self.host}/api/chat"
        options = {
            "temperature": 0.05,
            "top_p": 0.9,
            "num_ctx": self.num_ctx
        }
        if self.max_tokens:
            options["num_predict"] = self.max_tokens

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": options
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        full_content = []
        full_thinking = []

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue
                    try:
                        chunk = json.loads(line_str)
                    except json.JSONDecodeError:
                        continue

                    msg = chunk.get("message", {})
                    thinking_delta = msg.get("thinking", "")
                    content_delta = msg.get("content", "")

                    if thinking_delta:
                        full_thinking.append(thinking_delta)
                        yield {"type": "thinking", "token": thinking_delta}

                    if content_delta:
                        full_content.append(content_delta)
                        yield {"type": "content", "token": content_delta}

                    if chunk.get("done"):
                        break
        except Exception as e:
            raise RuntimeError(f"Failed during Ollama streaming from {url}: {e}")

        total_content = "".join(full_content).strip()
        total_thinking = "".join(full_thinking).strip()
        
        if not total_content and total_thinking:
            total_content = total_thinking

        return total_content, total_thinking

    def parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parses LLM output into either a SQL query or a direct conversational message.
        """
        if not response_text:
            return {"type": "sql", "sql": ""}

        # 1. Strip any <think>...</think> reasoning tags
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", response_text, flags=re.IGNORECASE).strip()

        # 2. Extract ```sql ... ``` or ``` ... ``` block if present (even if closing fence is omitted)
        match = re.search(r"```(?:sql)?\s*([\s\S]*?)(?:```|$)", cleaned, re.IGNORECASE)
        if match and match.group(1).strip():
            candidate = match.group(1).strip().strip("`").strip()
            if re.search(SQL_START_KEYWORDS, candidate, re.IGNORECASE):
                return {"type": "sql", "sql": candidate}

        # 3. Raw SQL statement (WITHOUT code blocks):
        # Must explicitly START with an SQL keyword at the beginning of the text
        raw_start = re.match(
            r"^\s*(SELECT|WITH|INSERT\s+INTO|UPDATE|DELETE\s+FROM|CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|TRUNCATE\s+TABLE)\b",
            cleaned,
            re.IGNORECASE
        )
        if raw_start:
            # Check if this is conversational prose containing conversational indicators
            conversational_markers = [
                "i cannot", "i am", "naturalsql", "sorry", "cannot be",
                "please clarify", "i can help", "if you need to", "you don't"
            ]
            if not any(marker in cleaned.lower() for marker in conversational_markers):
                return {"type": "sql", "sql": cleaned}

        # 4. If neither SQL block nor valid SQL statement found:
        return {
            "type": "conversational",
            "text": cleaned
        }

    def extract_sql(self, response_text: str) -> str:
        parsed = self.parse_response(response_text)
        if parsed.get("type") == "sql":
            return parsed.get("sql", "")
        return ""

    def _format_history(self, history: Optional[List[Dict[str, Any]]]) -> str:
        """
        Builds a compact summary of recent turns (strictly last 2 interactions).
        Keeps VRAM footprint minimal (~30-80 tokens) for 8GB VRAM environments.
        """
        if not history:
            return ""

        recent = history[-2:]
        lines = []
        for item in recent:
            q = (item.get("question") or "").strip() if isinstance(item, dict) else getattr(item, "question", "").strip()
            s = (item.get("sql") or "").strip() if isinstance(item, dict) else getattr(item, "sql", "").strip()
            r = (item.get("response") or "").strip() if isinstance(item, dict) else getattr(item, "response", "").strip()
            if q and s:
                lines.append(f'- User: "{q}" -> SQL: {s}')
            elif q and r:
                lines.append(f'- User: "{q}" -> Note: {r[:100]}')

        if not lines:
            return ""

        return (
            "RECENT CONVERSATION CONTEXT (last 1-2 interactions for resolving follow-ups):\n"
            + "\n".join(lines)
            + "\n\n"
        )

    def generate_stream(
        self,
        user_question: str,
        schema_text: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
        history_text = self._format_history(history)
        user_content = (
            f"DATABASE SCHEMA:\n\n{schema_text}\n\n"
            f"{history_text}"
            f"CURRENT QUESTION / TASK: {user_question}\n\n"
            f"INSTRUCTION: If this prompt can be answered or executed on the database, generate ONLY the SQL query in a ```sql ... ``` block. If the prompt references previous queries (e.g. 'order them', 'filter those', 'show their names'), use the recent conversation history above to resolve the context. If it cannot become an SQL query, respond directly in natural language:"
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        stream_gen = self._call_ollama_stream(messages)
        full_content = ""
        try:
            while True:
                token_item = next(stream_gen)
                yield token_item
        except StopIteration as e:
            full_content, _ = e.value

        return self.parse_response(full_content)

    def generate_repair_stream(
        self,
        user_question: str,
        schema_text: str,
        failed_sql: str,
        surgical_feedback: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Generator[Dict[str, Any], None, str]:
        history_text = self._format_history(history)
        repair_content = (
            f"DATABASE SCHEMA:\n\n{schema_text}\n\n"
            f"{history_text}"
            f"QUESTION: {user_question}\n\n"
            f"Your previous query was rejected:\n"
            f"```sql\n{failed_sql}\n```\n\n"
            f"ERROR FEEDBACK:\n{surgical_feedback}\n\n"
            f"INSTRUCTION:\n"
            f"Rewrite the SQL query to fix the exact error noted above. "
            f"Adhere strictly to the schema. Output ONLY valid SQL inside a ```sql ... ``` block."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": repair_content}
        ]

        stream_gen = self._call_ollama_stream(messages)
        full_content = ""
        try:
            while True:
                token_item = next(stream_gen)
                yield token_item
        except StopIteration as e:
            full_content, _ = e.value

        return self.extract_sql(full_content)

    def generate(self, user_question: str, schema_text: str) -> str:
        gen = self.generate_stream(user_question, schema_text)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            return e.value

    def generate_repair(self, user_question: str, schema_text: str, failed_sql: str, surgical_feedback: str) -> str:
        gen = self.generate_repair_stream(user_question, schema_text, failed_sql, surgical_feedback)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            return e.value
