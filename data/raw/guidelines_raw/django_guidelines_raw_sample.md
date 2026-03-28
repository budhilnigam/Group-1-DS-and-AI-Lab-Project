---
repo: django/django
repo_name: Django
storage_type: raw_guidelines
collected_on: 2026-03-21
collector: team_member_name
---

BEGIN_GUIDELINE_BLOCK
source_id: django_001
source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/
source_title: Coding style
section_hint: Python style
BEGIN_TEXT
All files should be formatted using the black auto-formatter. This will be run by pre-commit if that is configured.

The project repository includes an .editorconfig file. We recommend using a text editor with EditorConfig support to avoid indentation and whitespace issues. The Python files use 4 spaces for indentation and the HTML files use 2 spaces.

Unless otherwise specified, follow PEP 8.

Use flake8 to check for problems in this area. Note that our .flake8 file excludes some errors that we do not consider as gross violations. Remember that PEP 8 is only a guide, so respect the style of the surrounding code as a primary goal.

An exception to PEP 8 is our rules on line lengths. We allow up to 88 characters in code, as this is the line length used by black. Documentation, comments, and docstrings should be wrapped at 79 characters. These limits are checked when flake8 is run.

String variable interpolation may use %-formatting, f-strings, or str.format() as appropriate, with the goal of maximizing code readability.

Final judgments of readability are left to the Merger's discretion. As a guide, f-strings should use only plain variable and property access, with prior local variable assignment for more complex cases:

# Allowed
f"hello {user}"
f"hello {user.name}"
f"hello {self.user.name}"

# Disallowed
f"hello {get_user()}"
f"you are {user.age * 365.25} days old"

# Allowed with local variable assignment
user = get_user()
f"hello {user}"
user_days_old = user.age * 365.25
f"you are {user_days_old} days old"

f-strings should not be used for any string that may require translation, including error and logging messages. In general format() is more verbose, so the other formatting methods are preferred.

Do not waste time doing unrelated refactoring of existing code to adjust the formatting method.

Avoid use of "we" in comments, e.g. "Loop over" rather than "We loop over".
END_TEXT
END_GUIDELINE_BLOCK