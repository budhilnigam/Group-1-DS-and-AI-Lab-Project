import ast


def check_documentation_formatting_errors(file, min_docstring_len=10):
    """Return docstring/documentation formatting violations.

    Args:
        file (str): Path to a Python source file.
        min_docstring_len (int): Minimum non-whitespace docstring length.

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

    errors = []

    module_doc = ast.get_docstring(tree, clean=False)
    if module_doc is None:
        errors.append("Module: Missing module docstring.")
    elif len(module_doc.strip()) < min_docstring_len:
        errors.append(
            f"Module: Docstring too short (< {min_docstring_len} characters)."
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ds = ast.get_docstring(node, clean=False)
            if ds is None:
                errors.append(
                    f"Line {node.lineno}: Function '{node.name}' is missing a docstring."
                )
            elif len(ds.strip()) < min_docstring_len:
                errors.append(
                    f"Line {node.lineno}: Function '{node.name}' has a too-short docstring (< {min_docstring_len} characters)."
                )

        if isinstance(node, ast.ClassDef):
            ds = ast.get_docstring(node, clean=False)
            if ds is None:
                errors.append(
                    f"Line {node.lineno}: Class '{node.name}' is missing a docstring."
                )
            elif len(ds.strip()) < min_docstring_len:
                errors.append(
                    f"Line {node.lineno}: Class '{node.name}' has a too-short docstring (< {min_docstring_len} characters)."
                )

    return errors