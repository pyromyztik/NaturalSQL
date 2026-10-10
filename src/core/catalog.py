from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_target: Optional[str] = None  # e.g., "customers.customer_id"
    sample_values: List[str] = field(default_factory=list)
    description: Optional[str] = None

@dataclass
class TableInfo:
    name: str
    columns: Dict[str, ColumnInfo] = field(default_factory=dict)
    description: Optional[str] = None

    def add_column(self, col: ColumnInfo):
        self.columns[col.name.lower()] = col

    def get_column(self, col_name: str) -> Optional[ColumnInfo]:
        return self.columns.get(col_name.lower())

    @property
    def column_names(self) -> List[str]:
        return list(self.columns.keys())

class DatabaseCatalog:
    """
    Universal in-memory database catalog representing tables, columns,
    primary keys, foreign keys, and prompt formatting for text-to-SQL.
    """
    def __init__(self):
        self.tables: Dict[str, TableInfo] = {}

    def add_table(self, table: TableInfo):
        self.tables[table.name.lower()] = table

    def get_table(self, table_name: str) -> Optional[TableInfo]:
        return self.tables.get(table_name.lower())

    @property
    def table_names(self) -> List[str]:
        return list(self.tables.keys())

    def get_all_column_names(self) -> Dict[str, List[str]]:
        """Returns {table_name: [col1, col2, ...]}"""
        return {tbl: table.column_names for tbl, table in self.tables.items()}

    def to_prompt_schema(self, dialect: str = "oracle") -> str:
        """
        Formats catalog into a token-efficient, highly informative schema block for the LLM.
        """
        lines = [f"DATABASE SCHEMA ({dialect.upper()}):", ""]
        relationships = []

        for tbl_name, tbl in self.tables.items():
            lines.append(f"Table: {tbl_name}")
            for col_name, col in tbl.columns.items():
                col_desc = f"  - {col_name}: {col.data_type}"
                flags = []
                if col.is_primary_key:
                    flags.append("PK")
                if col.is_foreign_key and col.foreign_target:
                    flags.append(f"FK -> {col.foreign_target}")
                    relationships.append(f"  - {tbl_name}.{col_name} -> {col.foreign_target}")
                if col.sample_values:
                    flags.append(f"Allowed/Sample: {', '.join(repr(v) for v in col.sample_values)}")
                
                if flags:
                    col_desc += f" ({', '.join(flags)})"
                lines.append(col_desc)
            lines.append("")

        if relationships:
            lines.append("RELATIONSHIPS (JOIN PATHS):")
            lines.extend(relationships)
            lines.append("")

        return "\n".join(lines)
