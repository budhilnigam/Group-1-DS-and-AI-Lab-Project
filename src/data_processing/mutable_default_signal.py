import ast


def check_mutable_default_errors(file):
    """Return mutable-default violations for function arguments.

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
        # Keep this helper conservative: if parsing fails, avoid noisy false positives.
        return [f"Syntax parse error at line {exc.lineno}: {exc.msg}"]

    errors = []

    def _is_mutable_default(node):
        if isinstance(node, (ast.List, ast.Dict, ast.Set)):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in {"list", "dict", "set", "defaultdict"}:
                return True
            if isinstance(func, ast.Attribute) and func.attr in {"list", "dict", "set", "defaultdict"}:
                return True
        return False

    for n in ast.walk(tree):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        positional_args = list(n.args.posonlyargs) + list(n.args.args)
        positional_defaults = list(n.args.defaults)

        if positional_defaults:
            default_start = len(positional_args) - len(positional_defaults)
            for arg, default in zip(positional_args[default_start:], positional_defaults):
                if _is_mutable_default(default):
                    errors.append(
                        f"Line {getattr(default, 'lineno', n.lineno)}: "
                        f"Function '{n.name}' uses mutable default for argument '{arg.arg}'."
                    )

        for kw_arg, kw_default in zip(n.args.kwonlyargs, n.args.kw_defaults):
            if kw_default is not None and _is_mutable_default(kw_default):
                errors.append(
                    f"Line {getattr(kw_default, 'lineno', n.lineno)}: "
                    f"Function '{n.name}' uses mutable default for keyword-only argument '{kw_arg.arg}'."
                )

    return errors
