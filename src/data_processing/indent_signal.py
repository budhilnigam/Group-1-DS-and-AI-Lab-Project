import re

def check_indent_errors(file):
    """
    Checks for common spacing and indentation issues inspired by PEP 8/Flake8.

    Args:
        file (str): The path to the Python file to check.

    Returns:
        list: A list of error messages for spacing/indentation issues found.
    """
    errors = []
    allow_tabs = False
    with open(file, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    indent_stack = [0]
    file_uses_space_indentation = False
    file_uses_tab_indentation = False

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip('\n\r')
        stripped_line = line.lstrip(' \t')

        # Skip blank lines for indentation-stack checks.
        if stripped_line == '':
            if line.rstrip(' \t') != line:
                errors.append(f"Line {i}: Trailing whitespace found on an empty line.")
            continue


        # Category 1: Tab policy and mixed tab/space indentation.
        leading = line[:len(line) - len(stripped_line)]
        has_leading_spaces = ' ' in leading
        has_leading_tabs = '\t' in leading

        if has_leading_spaces:
            file_uses_space_indentation = True
        if has_leading_tabs:
            file_uses_tab_indentation = True

        if has_leading_tabs and not allow_tabs:
            errors.append(f"Line {i}: Tab indentation is not allowed; use spaces.")

        if has_leading_spaces and has_leading_tabs:
            errors.append(f"Line {i}: Mixed tabs and spaces in leading indentation.")


        # Category 2: 4-space indentation width checks.
        if has_leading_spaces and not has_leading_tabs:
            if len(leading) % 4 != 0:
                errors.append(f"Line {i}: Indentation is not a multiple of 4 spaces.")

        # Normalize indentation to visual columns (tab width 4) for structural checks.
        indent_columns = len(leading.expandtabs(4))


        # Category 3: Indentation level transitions (unexpected indent / bad dedent).
        if indent_columns > indent_stack[-1]:
            if indent_columns - indent_stack[-1] > 4:
                errors.append(
                    f"Line {i}: Indentation jumps by more than one level ({indent_stack[-1]} -> {indent_columns})."
                )
            indent_stack.append(indent_columns)
        elif indent_columns < indent_stack[-1]:
            while len(indent_stack) > 1 and indent_columns < indent_stack[-1]:
                indent_stack.pop()
            if indent_columns != indent_stack[-1]:
                errors.append(
                    f"Line {i}: Unaligned dedent level ({indent_columns}); does not match previous indentation levels."
                )
                # Recover by treating this as a new indentation anchor.
                indent_stack.append(indent_columns)


        # Category 4: Line-level spacing issues (whitespace and indentation-adjacent style).
        if line.rstrip(' \t') != line:
            errors.append(f"Line {i}: Trailing whitespace found.")

        if re.match(r'^[ \t]+$', leading) is None and leading:
            errors.append(f"Line {i}: Non-whitespace character found in indentation prefix.")

    if file_uses_space_indentation and file_uses_tab_indentation:
        errors.append("File-level: Inconsistent indentation style; both tabs and spaces are used.")

    return errors