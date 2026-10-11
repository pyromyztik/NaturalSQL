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
    is_mutation: bool = False
    mutation_type: Optional[str] = None

class ASTCompiler:
    """
    Compiler-style safety and repair gatekeeper for Text-to-SQL queries.
    Parses SQL into an AST, performs semantic catalog checks, applies rule-based
    auto-repairs (0 tokens), and generates surgical error feedback for hallucinated schemas.
    Identifies mutations (INSERT/UPDATE/DELETE/DDL) for human-in-the-loop approval.
    """
    def __init__(self, catalog: DatabaseCatalog, dialect: str = "oracle", default_limit: int = 50):
        self.catalog = catalog
        self.dialect = dialect.lower()
        if self.dialect.startswith("postgres"):
            self.read_dialect = "postgres"
        elif self.dialect.startswith("oracle"):
            self.read_dialect = "oracle"
        elif self.dialect.startswith("mysql"):
            self.read_dialect = "mysql"
        else:
            self.read_dialect = "sqlite"
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
            tree = sqlglot.parse_one(cleaned_sql, read=self.read_dialect)
        except ParseError as e:
            # Fallback to generic parsing if dialect-specific parse fails
            try:
                tree = sqlglot.parse_one(cleaned_sql)
            except ParseError as e2:
                return CompilationResult(
                    is_valid=False,
                    original_sql=cleaned_sql,
                    errors=[f"Syntax error: {str(e2)}"],
                    surgical_feedback=f"The SQL query has a syntax error: {str(e2)}. Please correct the syntax."
                )

        # 2. Safety & Mutation Classification
        mutation_types = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop,
            exp.TruncateTable, exp.Create, exp.Alter, exp.Command
        )
        is_mutation = any(tree.find_all(mutation_types))
        mutation_type = None

        if is_mutation:
            for mt, name in [
                (exp.Insert, "INSERT"),
                (exp.Update, "UPDATE"),
                (exp.Delete, "DELETE"),
                (exp.Drop, "DROP"),
                (exp.TruncateTable, "TRUNCATE"),
                (exp.Create, "CREATE TABLE"),
                (exp.Alter, "ALTER TABLE")
            ]:
                if any(tree.find_all(mt)):
                    mutation_type = name
                    break
            if not mutation_type:
                mutation_type = "DATA_MODIFICATION"

        # 3. Catalog & Semantic Verification
        # For CREATE statements, skip table existence check since table is new
        catalog_errors = []
        if not any(tree.find_all(exp.Create)):
            catalog_errors = self._validate_catalog(tree)
            catalog_errors.extend(self._validate_group_by_semantics(tree))
            
        if catalog_errors:
            feedback = "The query failed catalog and semantic validation against the database schema:\n"
            feedback += "\n".join(f"- {err}" for err in catalog_errors)
            feedback += "\nPlease correct the table, column names, and aggregation/GROUP BY rules."
            return CompilationResult(
                is_valid=False,
                original_sql=cleaned_sql,
                errors=catalog_errors,
                surgical_feedback=feedback,
                ast=tree,
                is_mutation=is_mutation,
                mutation_type=mutation_type
            )

        # 4. Tier 1: Rule-Based Auto-Patching (Zero tokens, only for SELECT)
        patches_applied = []
        if not is_mutation and isinstance(tree, exp.Select):
            tree = self._auto_patch_cross_join(tree, patches_applied)
            tree = self._auto_patch_group_by(tree, patches_applied)
            tree = self._auto_patch_limit(tree, patches_applied)

        # 5. Emit verified and patched SQL
        try:
            compiled_sql = tree.sql(dialect=self.read_dialect, pretty=True)
        except Exception:
            compiled_sql = cleaned_sql

        return CompilationResult(
            is_valid=True,
            original_sql=cleaned_sql,
            compiled_sql=compiled_sql,
            patches=patches_applied,
            ast=tree,
            is_mutation=is_mutation,
            mutation_type=mutation_type
        )

    def _validate_catalog(self, tree: exp.Expression) -> List[str]:
        """
        Validates tables and columns in the AST against the schema catalog.
        Recognizes projection aliases and CTEs.
        """
        errors = []
        known_tables = set(self.catalog.table_names)

        # If catalog is empty (new empty db), don't flag non-existent tables
        if not known_tables:
            return errors

        # 1. Detect CTEs
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

        # 2. Collect projection aliases defined in the query
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
                match = process.extractOne(tbl_name, list(self.catalog.table_names), scorer=fuzz.WRatio)
                suggestion = f" Did you mean '{match[0]}'?" if match and match[1] >= 60 else ""
                errors.append(f"Table '{tbl_name}' does not exist in schema.{suggestion}")
            else:
                referenced_tables.append(tbl_name)
                alias_name = (tbl.alias or tbl.name).lower()
                alias_map[alias_name] = tbl_name

        if not referenced_tables and known_tables:
            return errors

        # 4. Validate columns
        for col in tree.find_all(exp.Column):
            col_name = col.name.lower()
            if col_name == "*":
                continue

            tbl_qualifier = col.table.lower() if col.table else None

            if tbl_qualifier:
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
                if col_name in select_aliases:
                    continue

                found_in = [
                    tbl for tbl in referenced_tables
                    if (tbl in self.catalog.table_names and col_name in self.catalog.get_table(tbl).column_names)
                    or (tbl in cte_map and (not cte_map[tbl] or col_name in cte_map[tbl]))
                ]
                if not found_in and referenced_tables:
                    all_query_cols = []
                    for tbl in referenced_tables:
                        if tbl in self.catalog.table_names:
                            all_query_cols.extend(self.catalog.get_table(tbl).column_names)
                        elif tbl in cte_map:
                            all_query_cols.extend(cte_map[tbl])
                    
                    match = process.extractOne(col_name, all_query_cols, scorer=fuzz.WRatio)
                    suggestion = f" Did you mean '{match[0]}'?" if match and match[1] >= 60 else ""
                    errors.append(f"Column '{col_name}' not found in referenced tables ({', '.join(referenced_tables)}).{suggestion}")

        return errors

    def _validate_group_by_semantics(self, tree: exp.Expression) -> List[str]:
        """
        Validates that queries with GROUP BY do not project un-aggregated columns
        or un-aggregated columns inside window functions. Works across CTEs and main queries.
        """
        errors = []
        for select in tree.find_all(exp.Select):
            group = select.args.get("group")
            if not group:
                continue

            cte_ancestor = select.find_ancestor(exp.CTE)
            ctx = f"In CTE '{cte_ancestor.alias or cte_ancestor.name}': " if cte_ancestor else ""

            group_cols = set()
            for ge in group.expressions:
                for col in ge.find_all(exp.Column):
                    group_cols.add(col.sql().lower())
                    if hasattr(col, "name") and col.name:
                        group_cols.add(col.name.lower())

            check_nodes = list(select.selects)
            having = select.args.get("having")
            if having:
                check_nodes.append(having)

            for s in check_nodes:
                for col in s.find_all(exp.Column):
                    if col.find_ancestor(exp.Select) != select:
                        continue
                    if col.find_ancestor(exp.AggFunc) is not None:
                        continue
                    col_name = col.sql()
                    c_name = col.name if hasattr(col, "name") else ""
                    if col_name.lower() not in group_cols and c_name.lower() not in group_cols:
                        errors.append(
                            f"{ctx}Column '{col_name}' must appear in the GROUP BY clause or be used in an aggregate function."
                        )
        return errors

    def _auto_patch_cross_join(self, tree: exp.Expression, patches: List[str]) -> exp.Expression:
        if not isinstance(tree, exp.Select):
            return tree
        patched = False
        for j in tree.find_all(exp.Join):
            if (j.kind or "").upper() == "CROSS" and j.args.get("on"):
                j.set("kind", "")
                patched = True
        if patched:
            patches.append("Auto-patched: Converted invalid CROSS JOIN with ON clause to INNER JOIN")
        return tree

    def _auto_patch_group_by(self, tree: exp.Expression, patches: List[str]) -> exp.Expression:
        if not isinstance(tree, exp.Select):
            return tree

        # Identify genuine aggregate functions directly in the outer SELECT list
        # (Exclude window functions like AVG() OVER (...) and aggregates inside subqueries)
        outer_aggs = []
        for s in tree.selects:
            for agg in s.find_all(exp.AggFunc):
                if agg.find_ancestor(exp.Window) is None and agg.find_ancestor(exp.Select) == tree:
                    outer_aggs.append(agg)

        has_existing_group = bool(tree.args.get("group"))
        if not outer_aggs and not has_existing_group:
            return tree

        agg_subtrees = set()
        for agg in outer_aggs:
            agg_subtrees.update(agg.walk())

        existing_group = tree.args.get("group")
        existing_group_sql = set()
        if existing_group:
            for g_expr in existing_group.expressions:
                existing_group_sql.add(g_expr.sql().lower())

        missing_to_group = []
        seen = set(existing_group_sql)
        for select_expr in tree.selects:
            for node in select_expr.walk():
                if isinstance(node, exp.Column):
                    if node.find_ancestor(exp.Window) is not None:
                        continue
                    if node.find_ancestor(exp.Select) != tree:
                        continue
                    if node in agg_subtrees:
                        continue
                    col_sql = node.sql().lower()
                    if col_sql not in seen:
                        seen.add(col_sql)
                        missing_to_group.append(node)

        if missing_to_group:
            for col_node in missing_to_group:
                tree = tree.group_by(col_node, copy=False)
            col_names = [c.sql() for c in missing_to_group]
            patches.append(f"Auto-patched: Added missing columns to GROUP BY: {col_names}")

        return tree

    def _auto_patch_limit(self, tree: exp.Expression, patches: List[str]) -> exp.Expression:
        if self.default_limit and isinstance(tree, exp.Select) and not tree.args.get("limit"):
            tree = tree.limit(self.default_limit, copy=False)
            patches.append(f"Auto-patched: Injected safety LIMIT {self.default_limit}")
        return tree
