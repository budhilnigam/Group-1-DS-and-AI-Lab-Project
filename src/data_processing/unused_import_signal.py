import ast


def check_unused_import_errors(file):
    """Return probable unused-import violations from Python AST.

    Args:
        file (str): Path to a Python source file.

    Returns:
        list[str]: Human-readable violation messages.
    """
    try:
        with open(file, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as exc:
        return [f"File read error: {exc}"]

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"Syntax parse error at line {exc.lineno}: {exc.msg}"]

    imported = {}
    used = set()

    def add_import(name, lineno):
        if name == "*":
            return
        imported.setdefault(name, lineno)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname if alias.asname else alias.name.split(".")[0]
                add_import(bound, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname if alias.asname else alias.name
                add_import(bound, node.lineno)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)

    errors = []
    for name, lineno in imported.items():
        if name not in used and not name.startswith("_"):
            errors.append(f"Line {lineno}: Imported name '{name}' appears unused.")

    return errors
