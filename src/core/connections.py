import os
import re
import json
import time
import urllib.parse
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
import sqlglot

from .catalog import DatabaseCatalog, TableInfo, ColumnInfo

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONNECTIONS_FILE = os.path.join(BASE_DIR, "db", "connections.json")

def parse_connection_input(raw: str) -> Dict[str, Any]:
    """
    Parses a user-pasted connection string or terminal command into:
    - dialect: 'oracle' | 'postgres' | 'mysql' | 'sqlite'
    - engine_url: valid SQLAlchemy connection URL
    - display_url: safe URL for UI display (with passwords masked)
    """
    s = (raw or "").strip()
    # Strip terminal command prefixes like 'sql ', 'psql ', 'mysql '
    for prefix in ["sql ", "psql ", "mysql "]:
        if s.lower().startswith(prefix):
            s = s[len(prefix):].strip()

    # 1. Oracle EZConnect Shorthand:
    # format: [user]/[password]@[host]:[port]/[service_name]
    # e.g.: Pranav/despacito22@localhost:1521/FREEPDB1
    ez_match = re.match(r'^([^/:@]+)/([^@]+)@([^:/]+)(?::(\d+))?/(.+)$', s)
    if ez_match:
        user, pwd, host, port, service = ez_match.groups()
        port = port or "1521"
        engine_url = f"oracle+oracledb://{urllib.parse.quote_plus(user)}:{urllib.parse.quote_plus(pwd)}@{host}:{port}/?service_name={service}"
        display_url = f"{user}:****@{host}:{port}/{service}"
        return {
            "dialect": "oracle",
            "engine_url": engine_url,
            "display_url": display_url,
            "service_name": service,
            "user": user,
            "host": host,
            "port": int(port)
        }

    # 2. Oracle URL syntax: oracle:// or oracle+oracledb://
    if s.lower().startswith(("oracle://", "oracle+oracledb://")):
        cleaned = re.sub(r'^oracle(\+oracledb)?://', '', s, flags=re.IGNORECASE)
        # Parse user:pass@host:port/service
        match = re.match(r'^([^:@]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)$', cleaned)
        if match:
            user, pwd, host, port, service = match.groups()
            port = port or "1521"
            engine_url = f"oracle+oracledb://{urllib.parse.quote_plus(user)}:{urllib.parse.quote_plus(pwd)}@{host}:{port}/?service_name={service}"
            display_url = f"oracle://{user}:****@{host}:{port}/{service}"
            return {
                "dialect": "oracle",
                "engine_url": engine_url,
                "display_url": display_url,
                "service_name": service
            }
        else:
            return {
                "dialect": "oracle",
                "engine_url": s if "oracle+oracledb" in s else s.replace("oracle://", "oracle+oracledb://"),
                "display_url": re.sub(r':([^@]+)@', ':****@', s)
            }

    # 3. PostgreSQL URL syntax: postgres:// or postgresql://
    if s.lower().startswith(("postgres://", "postgresql://", "postgresql+psycopg2://")):
        engine_url = re.sub(r'^postgres://', 'postgresql+psycopg2://', s, flags=re.IGNORECASE)
        if not engine_url.lower().startswith("postgresql+psycopg2://"):
            engine_url = re.sub(r'^postgresql://', 'postgresql+psycopg2://', engine_url, flags=re.IGNORECASE)
        display_url = re.sub(r':([^@]+)@', ':****@', s)
        return {
            "dialect": "postgres",
            "engine_url": engine_url,
            "display_url": display_url
        }

    # PostgreSQL shorthand: user:password@host:port/dbname
    pg_short = re.match(r'^([^/:@]+):([^@]+)@([^:/]+):(\d+)/(.+)$', s)
    if pg_short and "5432" in s:
        user, pwd, host, port, db = pg_short.groups()
        engine_url = f"postgresql+psycopg2://{urllib.parse.quote_plus(user)}:{urllib.parse.quote_plus(pwd)}@{host}:{port}/{db}"
        display_url = f"{user}:****@{host}:{port}/{db}"
        return {
            "dialect": "postgres",
            "engine_url": engine_url,
            "display_url": display_url
        }

    # 4. MySQL URL syntax: mysql:// or mysql+pymysql://
    if s.lower().startswith(("mysql://", "mysql+pymysql://")):
        engine_url = re.sub(r'^mysql://', 'mysql+pymysql://', s, flags=re.IGNORECASE)
        display_url = re.sub(r':([^@]+)@', ':****@', s)
        return {
            "dialect": "mysql",
            "engine_url": engine_url,
            "display_url": display_url
        }

    # MySQL shorthand: user:password@host:3306/dbname
    if pg_short and "3306" in s:
        user, pwd, host, port, db = pg_short.groups()
        engine_url = f"mysql+pymysql://{urllib.parse.quote_plus(user)}:{urllib.parse.quote_plus(pwd)}@{host}:{port}/{db}"
        display_url = f"{user}:****@{host}:{port}/{db}"
        return {
            "dialect": "mysql",
            "engine_url": engine_url,
            "display_url": display_url
        }

    # 5. SQLite URI (if explicitly provided as a connection URI)
    if s.lower().startswith("sqlite:///"):
        return {
            "dialect": "sqlite",
            "engine_url": s,
            "display_url": s
        }

    raise ValueError(
        f"Unrecognized connection string format: '{s}'.\n"
        "Supported formats:\n"
        "- Oracle: Pranav/password@localhost:1521/FREEPDB1 or oracle://user:pass@host:1521/service\n"
        "- PostgreSQL: postgresql://user:password@localhost:5432/dbname\n"
        "- MySQL: mysql://user:password@localhost:3306/dbname"
    )

def get_engine_connect_args(engine_url: str, timeout: int = 4) -> Dict[str, Any]:
    """
    Returns driver-specific connection timeout arguments so offline/unreachable
    databases fail fast (within seconds) rather than blocking the application for minutes.
    """
    url_lower = engine_url.lower()
    if "oracle" in url_lower:
        return {"tcp_connect_timeout": float(timeout)}
    elif "postgres" in url_lower or "mysql" in url_lower:
        return {"connect_timeout": int(timeout)}
    elif "sqlite" in url_lower:
        return {"timeout": float(timeout)}
    return {}

def test_connection(connection_url: str) -> Dict[str, Any]:
    """Attempts to connect and count tables using SQLAlchemy."""
    info = parse_connection_input(connection_url)
    connect_args = get_engine_connect_args(info["engine_url"], timeout=4)
    engine = create_engine(info["engine_url"], pool_pre_ping=True, connect_args=connect_args)
    try:
        with engine.connect() as conn:
            insp = inspect(engine)
            tables = insp.get_table_names()
        return {
            "success": True,
            "dialect": info["dialect"],
            "display_url": info["display_url"],
            "table_count": len(tables),
            "tables": tables[:10]
        }
    except Exception as e:
        return {
            "success": False,
            "dialect": info.get("dialect", "unknown"),
            "display_url": info.get("display_url", connection_url),
            "error": str(e)
        }
    finally:
        engine.dispose()

def introspect_connection(engine_url: str, max_sample_values: int = 5) -> Tuple[DatabaseCatalog, str]:
    """
    Universally introspects any connected relational database into DatabaseCatalog
    using SQLAlchemy inspect. Works across Oracle, PostgreSQL, MySQL, and SQLite.
    """
    connect_args = get_engine_connect_args(engine_url, timeout=4)
    engine = create_engine(engine_url, pool_pre_ping=True, connect_args=connect_args)
    inspector = inspect(engine)
    dialect_name = engine.dialect.name
    
    # Normalize dialect name
    if dialect_name.startswith("oracle"):
        dialect = "oracle"
    elif dialect_name.startswith("postgres"):
        dialect = "postgres"
    elif dialect_name.startswith("mysql"):
        dialect = "mysql"
    else:
        dialect = "sqlite"

    cat = DatabaseCatalog()
    
    try:
        table_names = inspector.get_table_names()
        for tbl_name in table_names:
            tbl_info = TableInfo(name=tbl_name)
            
            # Primary keys
            pk_dict = inspector.get_pk_constraint(tbl_name) or {}
            pk_cols = set(pk_dict.get("constrained_columns") or [])
            
            # Columns
            for col in inspector.get_columns(tbl_name):
                col_name = col["name"]
                col_type = str(col.get("type", "VARCHAR"))
                is_pk = col_name in pk_cols
                tbl_info.add_column(ColumnInfo(
                    name=col_name,
                    data_type=col_type,
                    is_primary_key=is_pk
                ))
            
            # Foreign keys
            try:
                fks = inspector.get_foreign_keys(tbl_name) or []
                for fk in fks:
                    ref_tbl = fk.get("referred_table")
                    cols_from = fk.get("constrained_columns") or []
                    cols_to = fk.get("referred_columns") or []
                    for c_from, c_to in zip(cols_from, cols_to):
                        c = tbl_info.get_column(c_from)
                        if c and ref_tbl:
                            c.is_foreign_key = True
                            c.foreign_target = f"{ref_tbl}.{c_to}"
            except Exception:
                pass
            
            cat.add_table(tbl_info)
            
        return cat, dialect
    finally:
        engine.dispose()

def _json_serializable(val: Any) -> Any:
    """Recursively converts Decimals, dates, datetimes, bytes to JSON serializable objects."""
    if isinstance(val, Decimal):
        return float(val) if (val % 1 != 0) else int(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return val

def split_sql_statements(sql: str, dialect: str = "sqlite") -> List[str]:
    """
    Splits multi-statement SQL text into individual executable statements.
    Preserves semicolons inside string literals and comments.
    """
    clean_sql = (sql or "").strip()
    if not clean_sql:
        return []

    read_dialect = (
        "postgres" if dialect.startswith("postgres") else
        ("oracle" if dialect.startswith("oracle") else
        ("mysql" if dialect.startswith("mysql") else "sqlite"))
    )

    # 1. Try sqlglot parse
    try:
        parsed = [s for s in sqlglot.parse(clean_sql, read=read_dialect) if s]
        if parsed:
            return [s.sql(dialect=read_dialect) for s in parsed]
    except Exception:
        pass

    # 2. Tokenizer/quote-aware fallback
    statements = []
    current = []
    in_sq = False
    in_dq = False
    in_bt = False
    in_lc = False
    in_bc = False
    i = 0
    n = len(clean_sql)
    while i < n:
        ch = clean_sql[i]
        next_ch = clean_sql[i + 1] if i + 1 < n else ""
        if not (in_sq or in_dq or in_bt):
            if in_lc:
                if ch == "\n":
                    in_lc = False
                current.append(ch)
                i += 1
                continue
            elif in_bc:
                if ch == "*" and next_ch == "/":
                    in_bc = False
                    current.append(ch)
                    current.append(next_ch)
                    i += 2
                    continue
                current.append(ch)
                i += 1
                continue
            elif ch == "-" and next_ch == "-":
                in_lc = True
                current.append(ch)
                current.append(next_ch)
                i += 2
                continue
            elif ch == "/" and next_ch == "*":
                in_bc = True
                current.append(ch)
                current.append(next_ch)
                i += 2
                continue

        if ch == "'" and not (in_dq or in_bt):
            if in_sq and next_ch == "'":
                current.append(ch)
                current.append(next_ch)
                i += 2
                continue
            in_sq = not in_sq
            current.append(ch)
            i += 1
            continue
        elif ch == '"' and not (in_sq or in_bt):
            in_dq = not in_dq
            current.append(ch)
            i += 1
            continue
        elif ch == '`' and not (in_sq or in_dq):
            in_bt = not in_bt
            current.append(ch)
            i += 1
            continue

        if ch == ";" and not (in_sq or in_dq or in_bt or in_lc or in_bc):
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    rem = "".join(current).strip()
    if rem:
        statements.append(rem)

    return statements if statements else [clean_sql]

def execute_sql_query(engine_url: str, sql: str, is_mutation: bool = False) -> Dict[str, Any]:
    """
    Executes a SQL statement or multi-statement script on the connected database.
    - Handles single and multi-statement execution sequentially in the same transaction
    - Handles SELECT (fetches rows and column metadata)
    - Handles DML/DDL (INSERT/UPDATE/DELETE/ALTER/CREATE) with commit and rows_affected
    """
    t0 = time.time()
    connect_args = get_engine_connect_args(engine_url, timeout=5)
    engine = create_engine(engine_url, pool_pre_ping=True, connect_args=connect_args)
    try:
        dialect_name = engine.dialect.name.lower()
        statements = split_sql_statements(sql, dialect=dialect_name)
        if not statements:
            return {
                "success": True,
                "is_mutation": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "duration_ms": 0
            }

        last_result = None
        total_rows_affected = 0
        has_mutations = False

        with engine.connect() as conn:
            for stmt_str in statements:
                if not stmt_str.strip():
                    continue
                result = conn.execute(text(stmt_str))
                last_result = result
                stmt_upper = stmt_str.strip().upper()
                if is_mutation or stmt_upper.startswith(("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE")):
                    has_mutations = True
                    rc = getattr(result, "rowcount", 0)
                    if rc and rc > 0:
                        total_rows_affected += rc

            if has_mutations or is_mutation:
                conn.commit()

            duration_ms = round((time.time() - t0) * 1000)

            if last_result and last_result.returns_rows:
                columns = list(last_result.keys())
                raw_rows = last_result.fetchall()
                rows = []
                for row in raw_rows:
                    row_dict = {}
                    for col_name, val in zip(columns, row):
                        row_dict[col_name] = _json_serializable(val)
                    rows.append(row_dict)
                return {
                    "success": True,
                    "is_mutation": False,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "duration_ms": duration_ms
                }
            else:
                stmt_count = len(statements)
                status_msg = f"Executed {stmt_count} statements successfully" if stmt_count > 1 else "Executed successfully"
                return {
                    "success": True,
                    "is_mutation": True,
                    "rows_affected": max(total_rows_affected, 0),
                    "columns": ["status", "rows_affected"],
                    "rows": [{"status": status_msg, "rows_affected": max(total_rows_affected, 0)}],
                    "row_count": 1,
                    "duration_ms": duration_ms
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "columns": [],
            "rows": [],
            "row_count": 0,
            "duration_ms": round((time.time() - t0) * 1000)
        }
    finally:
        engine.dispose()

class ConnectionRegistry:
    """Manages saved database connections in db/connections.json."""
    def __init__(self, filepath: str = CONNECTIONS_FILE):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def clear_all(self):
        """Wipes all saved database connections."""
        self.save({})

    def load(self) -> Dict[str, Any]:
        self._ensure_file()
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, data: Dict[str, Any]):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add(self, name: str, raw_connection: str) -> Dict[str, Any]:
        parsed = parse_connection_input(raw_connection)
        test_res = test_connection(raw_connection)
        if not test_res.get("success"):
            raise ValueError(f"Connection test failed: {test_res.get('error')}")

        conn_id = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower()).strip('_')
        if not conn_id:
            conn_id = f"conn_{int(time.time())}"

        data = self.load()
        if conn_id in data:
            conn_id = f"{conn_id}_{int(time.time())}"

        entry = {
            "id": conn_id,
            "name": name.strip() or f"{parsed['dialect'].title()} Database",
            "dialect": parsed["dialect"],
            "connection_input": raw_connection.strip(),
            "engine_url": parsed["engine_url"],
            "display_url": parsed["display_url"],
            "created_at": time.time()
        }
        data[conn_id] = entry
        self.save(data)
        return entry

    def delete(self, conn_id: str) -> bool:
        data = self.load()
        if conn_id in data:
            del data[conn_id]
            self.save(data)
            return True
        return False

