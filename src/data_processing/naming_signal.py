import ast
import re


_SNAKE_CASE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_PASCAL_CASE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")


def check_naming_convention_errors(file):
    """Return naming-convention violations from Python AST.

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

    def _is_snake_case(name):
        return bool(_SNAKE_CASE_RE.match(name))

    def _is_pascal_case(name):
        return bool(_PASCAL_CASE_RE.match(name))

    def _is_dunder(name):
        return name.startswith("__") and name.endswith("__")

    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef):
            if not _is_pascal_case(n.name):
                errors.append(
                    f"Line {n.lineno}: Class name '{n.name}' should use PascalCase."
                )

        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_dunder(n.name) and not _is_snake_case(n.name):
                errors.append(
                    f"Line {n.lineno}: Function name '{n.name}' should use snake_case."
                )

            all_args = list(n.args.posonlyargs) + list(n.args.args) + list(n.args.kwonlyargs)
            if n.args.vararg is not None:
                all_args.append(n.args.vararg)
            if n.args.kwarg is not None:
                all_args.append(n.args.kwarg)

            for arg in all_args:
                arg_name = arg.arg
                if arg_name in {"self", "cls"}:
                    continue
                if not _is_snake_case(arg_name):
                    errors.append(
                        f"Line {arg.lineno}: Argument name '{arg_name}' should use snake_case."
                    )

    return errors
