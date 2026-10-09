from dataclasses import dataclass, field
from typing import Dict, List, Optional
import psycopg2

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

    def to_prompt_schema(self) -> str:
        """
        Formats catalog into a token-efficient, highly informative schema block for the LLM.
        """
        lines = ["DATABASE SCHEMA (PostgreSQL):", ""]
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

    @classmethod
    def create_sample_ecommerce(cls) -> "DatabaseCatalog":
        """
        Default rich e-commerce catalog for instant offline testing and benchmarking.
        """
        cat = cls()

        # Customers table
        cust = TableInfo(name="customers", description="Store customers and contact info")
        cust.add_column(ColumnInfo("customer_id", "INTEGER", is_primary_key=True))
        cust.add_column(ColumnInfo("full_name", "VARCHAR(100)"))
        cust.add_column(ColumnInfo("email", "VARCHAR(100)"))
        cust.add_column(ColumnInfo("city", "VARCHAR(50)", sample_values=["New York", "San Francisco", "Austin", "Chicago"]))
        cust.add_column(ColumnInfo("created_at", "TIMESTAMP"))
        cat.add_table(cust)

        # Products table
        prod = TableInfo(name="products", description="Product inventory catalog")
        prod.add_column(ColumnInfo("product_id", "INTEGER", is_primary_key=True))
        prod.add_column(ColumnInfo("product_name", "VARCHAR(150)"))
        prod.add_column(ColumnInfo("category", "VARCHAR(50)", sample_values=["Electronics", "Clothing", "Home", "Books"]))
        prod.add_column(ColumnInfo("unit_price", "NUMERIC(10,2)"))
        prod.add_column(ColumnInfo("stock_quantity", "INTEGER"))
        cat.add_table(prod)

        # Orders table
        orders = TableInfo(name="orders", description="Customer orders")
        orders.add_column(ColumnInfo("order_id", "INTEGER", is_primary_key=True))
        orders.add_column(ColumnInfo("customer_id", "INTEGER", is_foreign_key=True, foreign_target="customers.customer_id"))
        orders.add_column(ColumnInfo("order_date", "DATE"))
        orders.add_column(ColumnInfo("order_status", "VARCHAR(20)", sample_values=["pending", "shipped", "delivered", "cancelled"]))
        orders.add_column(ColumnInfo("total_amount", "NUMERIC(10,2)"))
        cat.add_table(orders)

        # Order Items table
        items = TableInfo(name="order_items", description="Line items for each order")
        items.add_column(ColumnInfo("item_id", "INTEGER", is_primary_key=True))
        items.add_column(ColumnInfo("order_id", "INTEGER", is_foreign_key=True, foreign_target="orders.order_id"))
        items.add_column(ColumnInfo("product_id", "INTEGER", is_foreign_key=True, foreign_target="products.product_id"))
        items.add_column(ColumnInfo("quantity", "INTEGER"))
        items.add_column(ColumnInfo("item_price", "NUMERIC(10,2)"))
        cat.add_table(items)

        return cat

    @classmethod
    def from_postgres(cls, connection_params: dict) -> "DatabaseCatalog":
        """
        Introspects a live PostgreSQL database schema from information_schema.
        """
        cat = cls()
        conn = psycopg2.connect(**connection_params)
        cursor = conn.cursor()

        # Query all user tables in public schema
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]

        for tbl_name in tables:
            tbl_info = TableInfo(name=tbl_name)

            # Query columns
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (tbl_name,))
            for col_name, data_type in cursor.fetchall():
                tbl_info.add_column(ColumnInfo(name=col_name, data_type=data_type))

            # Query Primary Keys
            cursor.execute("""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public'
                  AND tc.table_name = %s;
            """, (tbl_name,))
            for (pk_col,) in cursor.fetchall():
                col = tbl_info.get_column(pk_col)
                if col:
                    col.is_primary_key = True

            # Query Foreign Keys
            cursor.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
                  AND tc.table_name = %s;
            """, (tbl_name,))
            for fk_col, f_table, f_col in cursor.fetchall():
                col = tbl_info.get_column(fk_col)
                if col:
                    col.is_foreign_key = True
                    col.foreign_target = f"{f_table}.{f_col}"

            cat.add_table(tbl_info)

        cursor.close()
        conn.close()
        return cat
