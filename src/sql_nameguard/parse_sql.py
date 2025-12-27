import sqlglot
from sqlglot import expressions as exp


class SQLParser:
    """Robust SQL parser that extracts CTE names, column aliases, and table aliases.

    This implementation walks the sqlglot AST and collects:
    - CTEs (type: 'CTE')
    - Column aliases (type: 'column')
    - Table / subquery aliases (type: 'table')

    The parser de-duplicates results and returns a list of dicts with keys
    'alias', 'type', and 'code' (SQL for the aliased expression).
    """

    @staticmethod
    def _alias_to_str(alias_node):
        if alias_node is None:
            return None
        # Many sqlglot nodes expose .alias, .name, or .this; try common patterns
        try:
            if isinstance(alias_node, str):
                return alias_node
            if hasattr(alias_node, 'name') and alias_node.name:
                return alias_node.name
            if hasattr(alias_node, 'alias') and alias_node.alias:
                return alias_node.alias
            # fallback to string representation
            return str(alias_node)
        except Exception:
            return str(alias_node)

    @staticmethod
    def parse(sql: str):
        tree = sqlglot.parse_one(sql)
        results = []
        seen = set()

        def add(alias, typ, code):
            if not alias:
                return
            alias_str = SQLParser._alias_to_str(alias)
            code_str = code if isinstance(code, str) else (code.sql() if hasattr(code, 'sql') else str(code))
            key = (typ, alias_str, code_str)
            if key in seen:
                return
            seen.add(key)
            results.append({'alias': alias_str, 'type': typ, 'code': code_str})

        # Extract CTEs (find_all is robust across SQL structures)
        for cte in tree.find_all(exp.CTE):
            # cte.alias may be an Identifier or a simple name
            alias = getattr(cte, 'alias', None) or getattr(cte, 'alias_or_name', None)
            code_node = getattr(cte, 'this', None)
            add(alias, 'CTE', code_node)

        # Walk all Alias nodes and decide whether they are column aliases or table aliases
        for alias_node in tree.find_all(exp.Alias):
            inner = getattr(alias_node, 'this', None)
            alias_name = getattr(alias_node, 'alias', None) or getattr(alias_node, 'name', None)

            # If the inner expression is a Table/Subquery/Select, treat as table alias
            if isinstance(inner, (exp.Table, exp.Subquery, exp.Select)):
                add(alias_name, 'table', inner)
            else:
                # Otherwise treat as column alias (covers Column, Function, Expression aliases)
                add(alias_name, 'column', inner)

        # Some table aliases may be stored on Table nodes themselves
        for table in tree.find_all(exp.Table):
            alias = getattr(table, 'alias', None)
            if alias:
                add(alias, 'table', table)

        return results