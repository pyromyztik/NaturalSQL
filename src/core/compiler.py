from dataclasses import dataclass, field
from typing import List, Optional, Dict
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from rapidfuzz import process, fuzz

from .catalog import DatabaseCatalog

@dataclass
class CompilationResult:
    is_valid: bool
    original_sql: str
    compiled_sql: str = ""
    patches: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    surgical_feedback: Optional[str] = None
    ast: Optional[exp.Expression] = None

class ASTCompiler:
    """
    Compiler-style safety and repair gatekeeper for Text-to-SQL queries.
    Parses SQL into an AST, performs semantic catalog checks, applies rule-based
    auto-repairs (0 tokens), and generates surgical error feedback for hallucinated schemas.
    """
    def __init__(self, catalog: DatabaseCatalog, dialect: str = "postgres", default_limit: int = 50):
        self.catalog = catalog
        self.dialect = dialect
        self.default_limit = default_limit

    def clean_sql_input(self, raw_sql: str) -> str:
        """Strip markdown fences, leading/trailing whitespace."""
        cleaned = raw_sql.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    def compile(self, raw_sql: str) -> CompilationResult:
        cleaned_sql = self.clean_sql_input(raw_sql)
        if not cleaned_sql:
            return CompilationResult(
                is_valid=False,
                original_sql=raw_sql,
                errors=["Empty query provided."]
            )

        # 1. Parse AST
        try:
            tree = sqlglot.parse_one(cleaned_sql, read=self.dialect)
        except ParseError as e:
            return CompilationResult(
                is_valid=False,
                original_sql=cleaned_sql,
                errors=[f"Syntax error: {str(e)}"],
                surgical_feedback=f"The SQL query has a syntax error: {str(e)}. Please correct the syntax."
            )

        # 2. Safety & Read-Only Check
        destructive_types = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop,
            exp.TruncateTable, exp.Create, exp.Alter, exp.Command
        )
        if any(tree.find_all(destructive_types)):
            return CompilationResult(
                is_valid=False,
                original_sql=cleaned_sql,
                errors=["Security violation: Non-SELECT / destructive statements are strictly prohibited."],
                surgical_feedback="Security violation: The query attempted an INSERT, UPDATE, DELETE, or DROP. Only read-only SELECT queries are allowed."
            )

        # 3. Catalog Semantic Verification
        catalog_errors = self._validate_catalog(tree)
        if catalog_errors:
            feedback = "The query failed catalog validation against the database schema:\n"
            feedback += "\n".join(f"- {err}" for err in catalog_errors)
            feedback += "\nPlease correct the table and column names according to the schema."
            return CompilationResult(
                is_valid=False,
                original_sql=cleaned_sql,
                errors=catalog_errors,
                surgical_feedback=feedback,
                ast=tree
            )

        # 4. Tier 1: Rule-Based Auto-Patching (Zero tokens)
        patches_applied = []
        tree = self._auto_patch_group_by(tree, patches_applied)
        tree = self._auto_patch_limit(tree, patches_applied)

        # 5. Emit verified and patched SQL
        compiled_sql = tree.sql(dialect=self.dialect, pretty=True)

        return CompilationResult(
            is_valid=True,
            original_sql=cleaned_sql,
            compiled_sql=compiled_sql,
            patches=patches_applied,
            ast=tree
        )

    def _validate_catalog(self, tree: exp.Expression) -> List[str]:
        """
        Validates tables and columns in the AST against the schema catalog.
        Recognizes projection aliases (e.g. in ORDER BY, HAVING) and CTEs.
        Uses RapidFuzz to generate surgical suggestions for hallucinated identifiers.
        """
        errors = []
        known_tables = set(self.catalog.table_names)

        # 1. Detect CTEs (WITH cte_name AS (...))
        cte_map: Dict[str, List[str]] = {}
        for cte in tree.find_all(exp.CTE):
            cte_name = (cte.alias or cte.name).lower()
            cte_cols = []
            if isinstance(cte.this, exp.Select):
                for s in cte.this.selects:
                    if isinstance(s, exp.Alias):
                        cte_cols.append(s.alias.lower())
                    elif hasattr(s, "name") and s.name:
                        cte_cols.append(s.name.lower())
            cte_map[cte_name] = cte_cols
            known_tables.add(cte_name)

        # 2. Collect projection aliases defined in the query (e.g. SELECT COUNT(...) AS customer_count)
        select_aliases = set()
        for select_node in tree.find_all(exp.Select):
            for s in select_node.selects:
                if isinstance(s, exp.Alias):
                    select_aliases.add(s.alias.lower())
                elif hasattr(s, "alias_or_name") and s.alias_or_name:
                    select_aliases.add(s.alias_or_name.lower())

        # 3. Map table aliases to real table names
        alias_map: Dict[str, str] = {}
        referenced_tables: List[str] = []

        for tbl in tree.find_all(exp.Table):
            tbl_name = tbl.name.lower()
            if tbl_name not in known_tables:
                # Suggest closest table
                match = process.extractOne(tbl_name, list(self.catalog.table_names), scorer=fuzz.WRatio)
                suggestion = f" Did you mean '{match[0]}'?" if match and match[1] >= 60 else ""
                errors.append(f"Table '{tbl_name}' does not exist in schema.{suggestion}")
            else:
                referenced_tables.append(tbl_name)
                alias_name = (tbl.alias or tbl.name).lower()
                alias_map[alias_name] = tbl_name

        if not referenced_tables and known_tables:
            # Query might be selecting standalone literals or functions without tables
            return errors

        # 4. Validate columns
        for col in tree.find_all(exp.Column):
            col_name = col.name.lower()
            if col_name == "*":
                continue

            tbl_qualifier = col.table.lower() if col.table else None

            if tbl_qualifier:
                # Column is qualified: e.g. c.email or customers.email
                actual_table = alias_map.get(tbl_qualifier, tbl_qualifier)
                if actual_table in cte_map:
                    cte_cols = cte_map[actual_table]
                    if cte_cols and col_name not in cte_cols:
                        errors.append(f"Column '{col_name}' does not exist in CTE '{actual_table}'.")
                elif actual_table in self.catalog.table_names:
                    table_cols = self.catalog.get_table(actual_table).column_names
                    if col_name not in table_cols:
                        match = process.extractOne(col_name, table_cols, scorer=fuzz.WRatio)
                        suggestion = f" Did you mean '{match[0]}'?" if match and match[1] >= 60 else ""
                        errors.append(f"Column '{col_name}' does not exist in table '{actual_table}'.{suggestion}")
            else:
                # Column is unaliased: e.g. email or customer_count in ORDER BY
                # First, check if it matches a defined projection alias (valid in ORDER BY, HAVING, etc.)
                if col_name in select_aliases:
                    continue

                # Check if it exists in any of the tables referenced in this query
                found_in = [
                    tbl for tbl in referenced_tables
                    if (tbl in self.catalog.table_names and col_name in self.catalog.get_table(tbl).column_names)
                    or (tbl in cte_map and (not cte_map[tbl] or col_name in cte_map[tbl]))
                ]
                if not found_in and referenced_tables:
                    # Collect all available columns from referenced tables for fuzzy suggestion
                    all_query_cols = []
                    for tbl in referenced_tables:
                        if tbl in self.catalog.table_names:
                            all_query_cols.extend(self.catalog.get_table(tbl).column_names)
                        elif tbl in cte_map:
                            all_query_cols.extend(cte_map[tbl])
                    
                    match = process.extractOne(col_name, all_query_cols, scorer=fuzz.WRatio)
                    suggestion = f" Did you mean '{match[0]}'?" if match and match[1] >= 60 else ""
                    errors.append(f"Column '{col_name}' not found in referenced tables ({', '.join(referenced_tables)}).{suggestion}")
                    errors.append(f"Column '{col_name}' not found in referenced tables ({', '.join(referenced_tables)}).{suggestion}")

        return errors

    def _auto_patch_group_by(self, tree: exp.Expression, patches: List[str]) -> exp.Expression:
        """
        Rule-Based Fix:
        If the query has aggregate functions (COUNT, SUM, AVG, etc.) alongside bare column
        projections, but is missing GROUP BY clauses, automatically append them to the AST.
        """
        # Only applies to Select queries
        if not isinstance(tree, exp.Select):
            return tree

        # Check if query has an aggregate function
        has_aggregation = bool(list(tree.find_all(exp.AggFunc)))
        if not has_aggregation:
            return tree

        # Identify bare/non-aggregated column projections in SELECT
        non_agg_columns = []
        for select_expr in tree.selects:
            # If the expression contains no aggregate functions, it must be grouped
            if not list(select_expr.find_all(exp.AggFunc)):
                # If it's an alias, group by the underlying expression
                expr_to_group = select_expr.this if isinstance(select_expr, exp.Alias) else select_expr
                non_agg_columns.append(expr_to_group)

        if not non_agg_columns:
            return tree

        # Check existing GROUP BY expressions
        existing_group = tree.args.get("group")
        existing_group_sql = set()
        if existing_group:
            for g_expr in existing_group.expressions:
                existing_group_sql.add(g_expr.sql().lower())

        # Find columns that are missing from GROUP BY
        missing_to_group = [
            c for c in non_agg_columns
            if c.sql().lower() not in existing_group_sql
        ]

        if missing_to_group:
            for col_node in missing_to_group:
                tree = tree.group_by(col_node, copy=False)
            col_names = [c.sql() for c in missing_to_group]
            patches.append(f"Auto-patched: Added missing columns to GROUP BY: {col_names}")

        return tree

    def _auto_patch_limit(self, tree: exp.Expression, patches: List[str]) -> exp.Expression:
        """
        Rule-Based Guardrail:
        Automatically injects a LIMIT clause if one is not present, preventing accidental
        runaway full-table scans. (Disabled if default_limit is None).
        """
        if self.default_limit and isinstance(tree, exp.Select) and not tree.args.get("limit"):
            tree = tree.limit(self.default_limit, copy=False)
            patches.append(f"Auto-patched: Injected safety LIMIT {self.default_limit}")
        return tree
