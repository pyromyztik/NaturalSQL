import sqlite3
from .catalog import DatabaseCatalog, TableInfo, ColumnInfo

def catalog_from_sqlite(db_path: str) -> DatabaseCatalog:
    """Introspects an SQLite database into a DatabaseCatalog."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cat = DatabaseCatalog()

    # Get all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cur.fetchall()]

    for tbl_name in tables:
        t_info = TableInfo(name=tbl_name)
        
        # Columns: (cid, name, type, notnull, dflt_value, pk)
        cur.execute(f"PRAGMA table_info({tbl_name})")
        for col_row in cur.fetchall():
            c_name = col_row[1]
            c_type = col_row[2] or "TEXT"
            is_pk = bool(col_row[5])
            t_info.add_column(ColumnInfo(name=c_name, data_type=c_type, is_primary_key=is_pk))

        # Foreign keys: (id, seq, table, from, to, on_update, on_delete, match)
        cur.execute(f"PRAGMA foreign_key_list({tbl_name})")
        for fk_row in cur.fetchall():
            from_col = fk_row[3]
            target_tbl = fk_row[2]
            target_col = fk_row[4]
            col = t_info.get_column(from_col)
            if col:
                col.is_foreign_key = True
                col.foreign_target = f"{target_tbl}.{target_col}"

        cat.add_table(t_info)

    conn.close()
    return cat

if __name__ == "__main__":
    conn = sqlite3.connect("test_spider.db")
    conn.execute("CREATE TABLE singer (singer_id INT PRIMARY KEY, name TEXT, country TEXT, age INT)")
    conn.execute("CREATE TABLE concert (concert_id INT PRIMARY KEY, singer_id INT, concert_name TEXT, FOREIGN KEY(singer_id) REFERENCES singer(singer_id))")
    conn.close()

    cat = catalog_from_sqlite("test_spider.db")
    print(cat.to_prompt_schema())
