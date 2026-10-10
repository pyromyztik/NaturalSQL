"""
NaturalSQL: Universal Database Assistant and Safety Gatekeeper
"""
from src.core.catalog import DatabaseCatalog, TableInfo, ColumnInfo
from src.core.connections import (
    ConnectionRegistry,
    parse_connection_input,
    test_connection,
    introspect_connection,
    execute_sql_query
)
from src.core.compiler import ASTCompiler, CompilationResult
from src.generator import LLMGenerator
from src.streaming_pipeline import StreamingPipeline
import src.config as config

__all__ = [
    "DatabaseCatalog",
    "TableInfo",
    "ColumnInfo",
    "ConnectionRegistry",
    "parse_connection_input",
    "test_connection",
    "introspect_connection",
    "execute_sql_query",
    "ASTCompiler",
    "CompilationResult",
    "LLMGenerator",
    "StreamingPipeline",
    "config",
]
