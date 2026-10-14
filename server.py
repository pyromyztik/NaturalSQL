import os
import re
import json
import time
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.core.catalog import DatabaseCatalog, TableInfo, ColumnInfo
from src.core.connections import (
    ConnectionRegistry,
    parse_connection_input,
    test_connection,
    introspect_connection,
    execute_sql_query
)
from src.core.compiler import ASTCompiler
from src.generator import LLMGenerator
from src.streaming_pipeline import StreamingPipeline
from src import config

import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
connection_registry = ConnectionRegistry()

# In-memory cache of introspected catalogs: { conn_id: { ... } }
CATALOGS: Dict[str, Dict[str, Any]] = {}

def init_catalogs():
    """Initializes in-memory catalog metadata instantly from registry without blocking network I/O."""
    global CATALOGS
    saved_conns = connection_registry.load()
    for conn_id, meta in saved_conns.items():
        engine_url = meta.get("engine_url", "")
        CATALOGS[conn_id] = {
            "id": conn_id,
            "name": meta.get("name", conn_id.title()),
            "dialect": meta.get("dialect", "unknown"),
            "engine_url": engine_url,
            "display_url": meta.get("display_url", engine_url),
            "connection_input": meta.get("connection_input", ""),
            "catalog": DatabaseCatalog(),
            "status": "connecting",
            "error": None,
            "created_at": meta.get("created_at", time.time())
        }

def introspect_single_catalog(conn_id: str, meta: Dict[str, Any]):
    engine_url = meta.get("engine_url")
    if not engine_url:
        return
    try:
        cat, dialect = introspect_connection(engine_url)
        CATALOGS[conn_id] = {
            "id": conn_id,
            "name": meta.get("name", conn_id.title()),
            "dialect": dialect,
            "engine_url": engine_url,
            "display_url": meta.get("display_url", engine_url),
            "connection_input": meta.get("connection_input", ""),
            "catalog": cat,
            "status": "online",
            "error": None,
            "created_at": meta.get("created_at", time.time())
        }
        print(f"[Database] Successfully connected & introspected '{conn_id}' ({dialect.upper()}) with {len(cat.table_names)} tables.")
    except Exception as e:
        print(f"[Warning] Failed to introspect connection '{conn_id}': {e}")
        CATALOGS[conn_id] = {
            "id": conn_id,
            "name": meta.get("name", conn_id.title()),
            "dialect": meta.get("dialect", "unknown"),
            "engine_url": engine_url,
            "display_url": meta.get("display_url", engine_url),
            "connection_input": meta.get("connection_input", ""),
            "catalog": DatabaseCatalog(),
            "status": "offline",
            "error": str(e),
            "created_at": meta.get("created_at", time.time())
        }

def refresh_catalogs_async():
    """Introspects all saved connections concurrently in worker threads."""
    saved_conns = connection_registry.load()
    for conn_id, meta in saved_conns.items():
        executor.submit(introspect_single_catalog, conn_id, meta)

# Initialize metadata immediately so server starts in milliseconds
init_catalogs()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Concurrently introspect saved connections in background without delaying server start
    refresh_catalogs_async()
    yield
    executor.shutdown(wait=False)

app = FastAPI(title="NaturalSQL Universal", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    catalog_id: str
    execute: bool = True
    failed_sql: Optional[str] = None
    error_feedback: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None

class ExecuteSQLRequest(BaseModel):
    sql: str
    catalog_id: str
    user_approved: bool = False

class TestConnectionRequest(BaseModel):
    connection_string: str

class AddConnectionRequest(BaseModel):
    name: str
    connection_string: str

def format_catalog_response(info: Dict[str, Any]) -> Dict[str, Any]:
    cat: DatabaseCatalog = info.get("catalog") or DatabaseCatalog()
    tables_data = []
    for tbl_name in cat.table_names:
        tbl = cat.get_table(tbl_name)
        cols_data = []
        for col_name in tbl.column_names:
            c = tbl.get_column(col_name)
            cols_data.append({
                "name": c.name,
                "type": c.data_type,
                "is_primary_key": c.is_primary_key,
                "is_foreign_key": c.is_foreign_key,
                "foreign_target": c.foreign_target,
                "sample_values": c.sample_values
            })
        tables_data.append({
            "name": tbl.name,
            "description": tbl.description,
            "columns": cols_data
        })

    status = info.get("status")
    if not status:
        status = "offline" if info.get("error") else ("online" if tables_data else "connecting")

    return {
        "id": info["id"],
        "name": info["name"],
        "dialect": info["dialect"],
        "display_url": info.get("display_url", ""),
        "connection_input": info.get("connection_input", ""),
        "tables": tables_data,
        "status": status,
        "error": info.get("error"),
        "created_at": info.get("created_at")
    }

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "model": config.OLLAMA_MODEL,
        "ollama_host": config.OLLAMA_HOST,
        "connected_databases": list(CATALOGS.keys()),
        "time": time.time()
    }

@app.get("/api/catalogs")
@app.get("/api/connections")
async def get_connections(check: bool = False):
    if check:
        saved_conns = connection_registry.load()
        loop = asyncio.get_running_loop()
        futures = [
            loop.run_in_executor(executor, introspect_single_catalog, conn_id, meta)
            for conn_id, meta in saved_conns.items()
        ]
        if futures:
            await asyncio.gather(*futures)

    response = []
    for cat_id, info in CATALOGS.items():
        response.append(format_catalog_response(info))
    return response

@app.post("/api/connections/test")
async def api_test_connection(payload: TestConnectionRequest):
    if not payload.connection_string.strip():
        raise HTTPException(status_code=400, detail="Connection string cannot be empty.")
    result = test_connection(payload.connection_string)
    return result

@app.post("/api/connections")
async def add_connection(payload: AddConnectionRequest):
    if not payload.connection_string.strip():
        raise HTTPException(status_code=400, detail="Connection string is required.")
    
    clean_name = payload.name.strip()
    if not clean_name:
        clean_name = "Connected Database"

    try:
        entry = connection_registry.add(name=clean_name, raw_connection=payload.connection_string)
        cat, dialect = introspect_connection(entry["engine_url"])
        
        info = {
            "id": entry["id"],
            "name": entry["name"],
            "dialect": dialect,
            "engine_url": entry["engine_url"],
            "display_url": entry["display_url"],
            "connection_input": entry["connection_input"],
            "catalog": cat,
            "created_at": entry["created_at"]
        }
        CATALOGS[entry["id"]] = info
        
        return {
            "success": True,
            "message": f"Successfully connected to '{entry['name']}' ({dialect.upper()}) with {len(cat.table_names)} tables.",
            "catalog": format_catalog_response(info)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect: {str(e)}")

@app.delete("/api/connections")
async def forget_all_connections():
    connection_registry.clear_all()
    CATALOGS.clear()
    return {"success": True, "message": "All saved database connections have been forgotten."}

@app.delete("/api/connections/{connection_id}")
async def delete_connection(connection_id: str):
    if connection_id not in CATALOGS and connection_id not in connection_registry.load():
        raise HTTPException(status_code=404, detail="Connection not found.")
    
    connection_registry.delete(connection_id)
    if connection_id in CATALOGS:
        del CATALOGS[connection_id]
        
    return {"success": True, "message": f"Connection '{connection_id}' removed."}

@app.post("/api/connections/{connection_id}/refresh")
async def refresh_single_connection(connection_id: str):
    saved_conns = connection_registry.load()
    meta = saved_conns.get(connection_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Connection not found.")

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, introspect_single_catalog, connection_id, meta)

    info = CATALOGS.get(connection_id)
    if not info:
        raise HTTPException(status_code=404, detail="Connection not found after refresh.")

    return {
        "success": info.get("status") == "online",
        "message": f"Successfully connected to '{info.get('name')}'." if info.get("status") == "online" else f"Connection failed: {info.get('error')}",
        "catalog": format_catalog_response(info)
    }

@app.post("/api/connections/refresh")
async def refresh_all_connections():
    refresh_catalogs_async()
    return {"success": True, "message": "Refreshing all connections in background."}

@app.post("/api/chat/stream")
async def chat_stream(request: QueryRequest):
    cat_info = CATALOGS.get(request.catalog_id)
    if not cat_info:
        # If catalog_id not found, pick first online connection if available, else first connection
        online_conns = [c for c in CATALOGS.values() if not c.get("error") and c.get("status") == "online"]
        if online_conns:
            cat_info = online_conns[0]
        elif CATALOGS:
            cat_info = next(iter(CATALOGS.values()))
        else:
            raise HTTPException(status_code=400, detail="No active database connections configured. Please connect a database first.")

    if cat_info.get("status") == "offline" or cat_info.get("error"):
        raise HTTPException(
            status_code=503,
            detail=f"Database '{cat_info.get('name')}' is currently offline/unreachable: {cat_info.get('error')}. Please verify the database is running or switch to an online connection."
        )

    pipeline = StreamingPipeline(
        catalog=cat_info["catalog"],
        dialect=cat_info["dialect"],
        engine_url=cat_info.get("engine_url"),
    )

    async def event_generator():
        async for event in pipeline.run_stream(
            question=request.question,
            execute=request.execute,
            failed_sql=request.failed_sql,
            error_feedback=request.error_feedback,
            history=request.history
        ):
            yield {
                "event": "message",
                "data": event
            }

    return EventSourceResponse(event_generator())

@app.post("/api/execute-sql")
async def execute_manual_sql(request: ExecuteSQLRequest):
    cat_info = CATALOGS.get(request.catalog_id)
    if not cat_info:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    if cat_info.get("status") == "offline" or cat_info.get("error"):
        raise HTTPException(
            status_code=503,
            detail=f"Database '{cat_info.get('name')}' is currently offline/unreachable: {cat_info.get('error')}. Please verify the database is running or switch to an online connection."
        )

    engine_url = cat_info.get("engine_url")
    if not engine_url:
        raise HTTPException(status_code=500, detail="Database connection string not configured.")

    # AST check to classify query
    compiler = ASTCompiler(catalog=cat_info["catalog"], dialect=cat_info["dialect"])
    compilation = compiler.compile(request.sql)

    is_mutation = compilation.is_mutation if compilation.is_valid else (
        any(k in request.sql.upper() for k in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE"))
    )

    # STRICT SAFETY GUARD: If statement is a mutation, require user_approved
    if is_mutation and not request.user_approved:
        raise HTTPException(
            status_code=403,
            detail=f"Explicit user approval is required to execute mutating SQL statements ({compilation.mutation_type or 'MODIFICATION'})."
        )

    exec_result = execute_sql_query(engine_url, request.sql, is_mutation=is_mutation)

    # If DDL modified schema (CREATE/DROP/ALTER), refresh cached catalog
    if exec_result.get("success") and any(k in request.sql.upper() for k in ["CREATE", "DROP", "ALTER"]):
        try:
            new_cat, _ = introspect_connection(engine_url)
            cat_info["catalog"] = new_cat
        except Exception as e:
            print(f"[Warning] Failed to re-introspect catalog after DDL: {e}")

    return exec_result

# Mount static files if frontend is built
frontend_dist = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
