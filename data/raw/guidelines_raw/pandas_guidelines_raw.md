---

repo: pandas-dev/pandas
repo_name: pandas
storage_type: raw_guidelines
collected_on: 2026-03-23
collector: Jeevika

---

BEGIN_GUIDELINE_BLOCK
source_id: pandas_001
source_url: doc/source/development/contributing.rst
source_title: Contributing to pandas
section_hint: Pull request title conventions

BEGIN_TEXT

Pull request title conventions

* Write a descriptive title that includes prefixes.
* pandas uses a convention for title prefixes:

  * ENH: Enhancement, new functionality
  * BUG: Bug fix
  * DOC: Additions/updates to documentation
  * TST: Additions/updates to tests
  * BLD: Updates to the build process/scripts
  * PERF: Performance improvement
  * TYP: Type annotations
  * CLN: Code cleanup

Updating your pull request

* Based on the review, make necessary changes to the code.

Tips for a successful pull request

* Reference an open issue for non-trivial changes.
* Ensure you have appropriate tests.
* Keep pull requests as simple as possible.
* Ensure that CI is in a green state.
* Keep updating your pull request regularly.

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_002
source_url: doc/source/development/contributing.rst
source_title: Contributing to pandas
section_hint: Code standards

BEGIN_TEXT

Code standards

* Writing good code is about how you write it.
* Continuous Integration runs tools to check stylistic errors.
* Any warning will cause the test to fail.
* Good style is required for submitting code.

Tools for verification

* ./ci/code_checks.sh
  * Validates doctests, modules, and notebooks.
  * Can run with parameters: code, doctests, notebooks.
* pre-commit
  * Used for code checks (explained separately).

Backward compatibility

* Avoid breaking existing user code.
* Maintain backward compatibility as much as possible.

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_003
source_url: doc/source/development/contributing.rst
source_title: Contributing to pandas
section_hint: Pre-commit

BEGIN_TEXT

Pre-commit

* Continuous Integration runs checks using:
  * ruff
  * isort
  * clang-format
  * pre-commit hooks

* Install pre-commit and run:

  pre-commit install

* This runs checks automatically on commit.

Usage without install

* pre-commit run --files <files you have modified>
* pre-commit run --from-ref=upstream/main --to-ref=HEAD --all-files

Manual checks

* pre-commit run --hook-stage manual --all-files

Additional notes

* You can skip checks using:
  * git commit --no-verify
* Run cleanup periodically:
  * pre-commit gc
* virtualenv conflicts may cause errors.
* If using conda, downgrade virtualenv to 20.0.33 if needed.
* Update environment after merging upstream changes.

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_004
source_url: doc/source/development/contributing.rst
source_title: Contributing to pandas
section_hint: Optional dependencies

BEGIN_TEXT

Optional dependencies

* Import using:
  * pandas.compat._optional.import_optional_dependency
* Ensures consistent error messages.

Testing

* Methods must include tests for ImportError.
* Skip test if dependency is present.

Documentation

* Document all optional dependencies.
* Set minimum version in:
  * pandas.compat._optional.VERSIONS

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_005
source_url: doc/source/development/contributing.rst
source_title: Contributing to pandas
section_hint: Backwards compatibility

BEGIN_TEXT

Backwards compatibility

* Maintain backward compatibility whenever possible.
* Clearly state reasons if breaking changes are required.
* Add deprecation warnings when needed.
* Add deprecated directive to functions.

Using deprecate helper

from pandas.util._decorators import deprecate

deprecate('old_func', 'new_func', '1.1.0')

Manual deprecation

import warnings
from pandas.util._exceptions import find_stack_level

def old_func():
    """Summary of the function.

    deprecated:: 1.1.0
       Use new_func instead.
    """
    warnings.warn(
        'Use new_func instead.',
        FutureWarning,
        stacklevel=find_stack_level(),
    )
    new_func()

def new_func():
    pass

Required updates

* Write tests asserting warnings.
* Update existing tests and code.

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_006
source_url: doc/source/development/contributing.rst
source_title: Contributing to pandas
section_hint: Type hints

BEGIN_TEXT

Type hints

* Use PEP 484 style type hints.
* New code should include type hints.
* Contributions adding type hints are encouraged.

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_007
source_url: doc/source/development/contributing_codebase.rst
source_title: Contributing to the Codebase
section_hint: Style guidelines - imports

BEGIN_TEXT

Style guidelines

* Use:
  * from typing import ...
* Code may be auto-rewritten by pre-commit checks.
* Prefer built-in types (e.g., list instead of typing.List).

Shadowing builtins

* Some classes may define variables shadowing builtins.
* Create alias to avoid ambiguity.

Example

class SomeClass1:
    str = None

str_type = str

class SomeClass2:
    str: str_type = None

Use of cast

* Using cast is strongly discouraged.
* Example (not preferred):

from typing import cast
from pandas.core.dtypes.common import is_number

def cannot_infer_bad(obj: Union[str, int, float]):

    if is_number(obj):
        ...
    else:
        obj = cast(str, obj)
        return obj.upper()

Preferred approach

def cannot_infer_good(obj: Union[str, int, float]):

    if isinstance(obj, str):
        return obj.upper()
    else:
        ...

* Refactor code instead of relying on cast.
* Exceptions allowed only when unavoidable.

pandas-specific types

* Use types from:
  * pandas._typing
* This module is private for pandas development.

User-facing types

* Expose in:
  * pandas.api.typing.aliases
* Add to pandas-stubs project when applicable.

Example

from pandas._typing import Dtype

def as_type(dtype: Dtype) -> ...:
    ...

Notes

* Module includes reusable types like:
  * path-like
  * array-like
  * numeric
* Also includes aliases like axis.
* Refer to source for latest types.

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_008
source_url: doc/source/development/contributing_codebase.rst
source_title: Contributing to the Codebase
section_hint: Documenting - release notes and references

BEGIN_TEXT

Documenting your code

* Changes should be reflected in the release notes located in doc/source/whatsnew/vx.y.z.rst.
* This file contains an ongoing change log for each release.
* Add an entry to document your fix, enhancement or breaking change.
* Include the GitHub issue number using :issue:`1234`.
* Entries should use full sentences and proper grammar.

Referencing API

* Use Sphinx directives when mentioning API:
  * :func:
  * :meth:
  * :class:
* Add links only if they resolve.
* Refer to previous release notes for examples.

Bugfix documentation

* Add entry to the relevant bugfix section.
* Avoid using the Other section unless necessary.
* Keep descriptions concise.
* Include:
  * how the user encounters the bug
  * indication of the issue (e.g. produces incorrect results)
* May include new behavior if needed.

Enhancement documentation

* Add usage examples to documentation.
* Follow documentation section guidelines.
* Use versionadded directive:

  .. versionadded:: 2.1.0

* This displays: New in version 2.1.0
* Add to:
  * docstrings for new functions/methods
  * new keyword arguments

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_009
source_url: doc/source/development/contributing_codebase.rst
source_title: Contributing to the Codebase
section_hint: Docstrings overview and standards

BEGIN_TEXT

Docstrings and standards

* A docstring documents modules, classes, functions, or methods.
* Helps understand functionality without reading implementation.
* Used to generate HTML documentation.
* Sphinx is used for documentation generation.

Docstring standards

* Follow PEP-257 conventions.
* pandas follows NumPy docstring convention.
* Refer to:
  * numpydoc docstring guide
* numpydoc is a Sphinx extension.

reStructuredText (reST)

* Used as markup language.
* Allows encoding styles in plain text.
* References:
  * Sphinx reStructuredText primer
  * Quick reStructuredText reference
  * Full reStructuredText specification

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_010
source_url: doc/source/development/contributing_codebase.rst
source_title: Contributing to the Codebase
section_hint: Writing docstrings - general rules

BEGIN_TEXT

Writing a docstring

General rules

* Use triple double-quotes.
* No blank lines before or after docstring.
* Text starts on next line after opening quotes.
* Closing quotes on separate line.

Inline code usage

* Use backticks for:
  * parameter names
  * Python code, modules, types, literals
  * pandas classes (:class:)
  * pandas methods (:meth:)
  * pandas functions (:func:)

Display behavior

* Use ~ prefix to shorten display of links.

Good example

def add_values(arr):
    """
    Add the values in arr.

    This is equivalent to Python sum of pandas.Series.sum.

    Some sections are omitted here for simplicity.
    """
    return sum(arr)

Bad example

def func():

    """Some function.

    With several mistakes in the docstring.

    It has a blank line after the signature def func():.

    The text should start after opening quotes.

    There is a blank line between docstring and code.

    Closing quotes should be on separate line."""

    foo = 1
    bar = 2
    return foo + bar

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_011
source_url: doc/source/development/contributing_codebase.rst
source_title: Contributing to the Codebase
section_hint: Docstring sections

BEGIN_TEXT

Section 1: short summary

* Single sentence describing function.
* Must:
  * start with capital letter
  * end with a dot
  * fit in one line
* Use infinitive verb.

Good examples

def astype(dtype):
    """
    Cast Series type.

    This section will provide further details.
    """
    pass

Bad examples

def astype(dtype):
    """
    Casts Series type.
    """
    pass

def astype(dtype):
    """
    Method to cast Series type.
    """
    pass

def astype(dtype):
    """
    Cast Series type
    """
    pass

def astype(dtype):
    """
    Cast Series type from its current type to the new type defined in the parameter dtype.
    """
    pass

Section 2: extended summary

* Provides detailed explanation.
* Does not include:
  * parameter details
  * implementation notes
* Leave blank line after short summary.
* Each paragraph ends with a dot.
* Explain usefulness and use cases.

Example

def unstack():
    """
    Pivot a row index to columns.

    When using a MultiIndex, a level can be pivoted so each value in
    the index becomes a column. This is especially useful when a subindex
    is repeated for the main index, and data is easier to visualize as a
    pivot table.

    The index level will be automatically removed from the index when added
    as columns.
    """
    pass

Section 3: parameters

* Title: Parameters
* Underline with hyphens.
* No blank line after title.
* Document all parameters except self.
* Include:
  * name
  * type
  * description

Formatting rules

* Format:
  * name : type
* Include space before colon.
* Description:
  * indented
  * starts with capital letter
  * ends with a dot

Defaults

* Format:
  * int, default 0
* Optional values:
  * str, optional
* Use "default None" only when None is actual value.

Good example

class Series:
    def plot(self, kind, color='blue', **kwargs):
        """
        Generate a plot.

        Render the data in the Series as a matplotlib plot of the specified kind.

        Parameters
        ----------
        kind : str
            Kind of matplotlib plot.
        color : str, default 'blue'
            Color name or rgb code.
        **kwargs
            These parameters will be passed to the matplotlib plotting function.
        """
        pass

Bad example

class Series:
    def plot(self, kind, **kwargs):
        """
        Generate a plot.

        Render the data in the Series as a matplotlib plot.

        Parameters
        ----------

        kind: str
            kind of matplotlib plot
        """
        pass

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_012
source_url: doc/source/development/contributing_docstring.rst
source_title: pandas docstring guide
section_hint: Parameter types

BEGIN_TEXT

Parameter types

* Use Python built-in data types directly:
  * int
  * float
  * str
  * bool

Complex types

* Define subtypes explicitly.
* Use brackets for readability:
  * list of int
  * dict of {str : int}
  * tuple of (str, int, int)
  * tuple of (str,)
  * set of str

Allowed values

* Use curly brackets and separate with commas.
* Maintain order if values are ordinal.
* Otherwise, list default value first.

Examples:

* {0, 10, 25}
* {'simple', 'advanced'}
* {'low', 'medium', 'high'}
* {'cat', 'dog', 'bird'}

Module types

* Specify module when needed:
  * datetime.date
  * datetime.datetime
  * decimal.Decimal

Package types

* Specify full path:
  * numpy.ndarray
  * scipy.sparse.coo_matrix

pandas types
* Use pandas prefix except for:
  * Series
  * DataFrame

Examples:
* Series
* DataFrame
* pandas.Index
* pandas.Categorical
* pandas.arrays.SparseArray

Generic types

* Use:
  * array-like
  * iterable

Multiple types
* Separate using commas.
* Last two types separated by 'or'.

Examples:
* int or float
* float, decimal.Decimal or None
* str or list of str

None handling
* Always place None at the end.

Axis convention
* axis : {0 or 'index', 1 or 'columns', None}, default None

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_013
source_url: doc/source/development/contributing_docstring.rst
source_title: pandas docstring guide
section_hint: Returns or Yields

BEGIN_TEXT

Section 4: returns or yields

* Document returned or yielded values in this section.
* Section title:
  * Returns or Yields
  * Followed by hyphen underline.

Formatting rules

* Similar to Parameters section.
* No name required unless multiple values.
* Use same type conventions as Parameters.
* Description must end with a dot.

Single return example

def sample():
    """
    Generate and return a random number.

    The value is sampled from a continuous uniform distribution between
    0 and 1.

    Returns
    -------
    float
        Random number generated.
    """
    return np.random.random()

Multiple return example

import string

def random_letters():
    """
    Generate and return a sequence of random letters.

    The length of the returned string is also random, and is also
    returned.

    Returns
    -------
    length : int
        Length of the returned string.
    letters : str
        String of random letters.
    """
    length = np.random.randint(1, 10)
    letters = ''.join(np.random.choice(string.ascii_lowercase)
                      for i in range(length))
    return length, letters

Yields example

def sample_values():
    """
    Generate an infinite sequence of random numbers.

    The values are sampled from a continuous uniform distribution between
    0 and 1.

    Yields
    ------
    float
        Random number generated.
    """
    while True:
        yield np.random.random()

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_014
source_url: doc/source/development/contributing_docstring.rst
source_title: pandas docstring guide
section_hint: Section 5: see also

BEGIN_TEXT

Section 5: see also

Purpose

* Used to highlight related pandas functionality.
* Can be skipped if no related methods exist.

Examples of related functionality

* head() and tail()
  * tail() provides equivalent functionality at the end instead of the beginning.

* loc and iloc
  * Same functionality with different input types (indices vs positions).

* max and min
  * Opposite operations.

* iterrows, itertuples and items
  * Different ways to iterate (rows vs columns).

* fillna and dropna
  * Both handle missing values.

* read_csv and to_csv
  * Complementary operations.

* merge and join
  * One is a generalization of the other.

* astype and pandas.to_datetime
  * Used for type casting, especially for dates.

* where and numpy.where
  * pandas functionality is based on numpy equivalent.

Guidelines for choosing related items

* Use common sense.
* Focus on what is helpful to users.
* Especially consider less experienced users.

External libraries

* Use full module names:
  * numpy (not np)
  * scipy.sparse.coo_matrix (full path if not top-level module)

Formatting rules

* Section title:
  * See Also
  * Capital S and A
* Followed by a hyphen underline.
* Preceded by a blank line.

Structure

* One line per related item:
  * function_name : description

Description rules

* Must:
  * explain functionality
  * explain relevance
  * highlight key differences
  * end with a dot

Line formatting

* Description is on the same line (unlike Returns/Yields).
* If too long:
  * continue on next line
  * indent further

Example

class Series:
    def head(self):
        """
        Return the first 5 elements of the Series.

        This function is mainly useful to preview the values of the
        Series without displaying the whole of it.

        Returns
        -------
        Series
            Subset of the original series with the 5 first values.

        See Also
        --------
        Series.tail : Return the last 5 elements of the Series.
        Series.iloc : Return a slice of the elements in the Series,
            which can also be used to return the first or last n.
        """
        return self.iloc[:5]

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_015
source_url: doc/source/development/contributing_docstring.rst
source_title: pandas docstring guide
section_hint: docstring examples

BEGIN_TEXT

Section 7: examples

Importance

* One of the most important sections of a docstring.
* Helps users understand concepts through examples.
* Often more effective than explanations.

General rules

* Examples must:
  * be valid Python code
  * produce deterministic output
  * be copy-paste runnable

Formatting

* Presented as Python terminal session:
  * >>> for code
  * ... for continuation
* Output appears immediately after code.
* No blank lines between code and output.
* Comments can be added with blank lines around them.

Structure of examples

1. Import required libraries (except numpy and pandas)
2. Create required data
3. Show a basic example (common use case)
4. Add extended examples with explanations

Example

class Series:

    def head(self, n=5):
        """
        Return the first elements of the Series.

        This function is mainly useful to preview the values of the
        Series without displaying all of it.

        Parameters
        ----------
        n : int
            Number of values to return.

        Return
        ------
        pandas.Series
            Subset of the original series with the n first values.

        See Also
        --------
        tail : Return the last n elements of the Series.

        Examples
        --------
        >>> ser = pd.Series(['Ant', 'Bear', 'Cow', 'Dog', 'Falcon',
        ...                'Lion', 'Monkey', 'Rabbit', 'Zebra'])
        >>> ser.head()
        0   Ant
        1   Bear
        2   Cow
        3   Dog
        4   Falcon
        dtype: object

        With the ``n`` parameter, we can change the number of returned rows:

        >>> ser.head(n=3)
        0   Ant
        1   Bear
        2   Cow
        dtype: object
        """
        return self.iloc[:n]

Conciseness

* Keep examples as concise as possible.
* For complex cases:
  * use sections with bold headers (**text**)

Conventions for examples

Implicit imports

* Assume these are already imported:
  * import numpy as np
  * import pandas as pd

Explicit imports

* Import other modules explicitly:
  * one per line
  * avoid aliases
* Order:
  * standard library first
  * third-party libraries next

Naming conventions

* Series → ser
* DataFrame → df
* Index → idx

Multiple objects

* Homogeneous:
  * ser1, ser2, ser3
  * df1, df2, df3
* Heterogeneous:
  * meaningful names (e.g. df_main, df_to_join)

Data guidelines

* Keep data compact.
* Recommended ~4 rows (adjust if needed).
* Use simple values (e.g. [1, 2, 3] for mean).

Complex examples

* Avoid random meaningless data.
* Use meaningful scenarios.
* Prefer animal-based naming for consistency.
* Use meaningful numeric properties.

Arguments

* Prefer keyword arguments:
  * head(n=3)
* Avoid positional arguments:
  * head(3)

Good examples

class Series:

    def mean(self):
        """
        Compute the mean of the input.

        Examples
        --------
        >>> ser = pd.Series([1, 2, 3])
        >>> ser.mean()
        2
        """
        pass


    def fillna(self, value):
        """
        Replace missing values by ``value``.

        Examples
        --------
        >>> ser = pd.Series([1, np.nan, 3])
        >>> ser.fillna(0)
        [1, 0, 3]
        """
        pass

    def groupby_mean(self):
        """
        Group by index and return mean.

        Examples
        --------
        >>> ser = pd.Series([380., 370., 24., 26],
        ...               name='max_speed',
        ...               index=['falcon', 'falcon', 'parrot', 'parrot'])
        >>> ser.groupby_mean()
        index
        falcon    375.0
        parrot     25.0
        Name: max_speed, dtype: float64
        """
        pass

    def contains(self, pattern, case_sensitive=True, na=numpy.nan):
        """
        Return whether each value contains ``pattern``.

        In this case, we are illustrating how to use sections, even
        if the example is simple enough and does not require them.

        Examples
        --------
        >>> ser = pd.Series('Antelope', 'Lion', 'Zebra', np.nan)
        >>> ser.contains(pattern='a')
        0    False
        1    False
        2     True
        3      NaN
        dtype: bool

        **Case sensitivity**

        With ``case_sensitive`` set to ``False`` we can match ``a`` with both
        ``a`` and ``A``:

        >>> s.contains(pattern='a', case_sensitive=False)
        0     True
        1    False
        2     True
        3      NaN
        dtype: bool

        **Missing values**

        We can fill missing values in the output using the ``na`` parameter:

        >>> ser.contains(pattern='a', na=False)
        0    False
        1    False
        2     True
        3    False
        dtype: bool
        """
        pass

Bad examples

def method(foo=None, bar=None):
    """
    A sample DataFrame method.

    Do not import NumPy and pandas.

    Try to use meaningful data, when it makes the example easier
    to understand.

    Try to avoid positional arguments like in df.method(1). They
    can be all right if previously defined with a meaningful name,
    like in present_value(interest_rate), but avoid them otherwise.

    When presenting the behavior with different parameters, do not place
    all the calls one next to the other. Instead, add a short sentence
    explaining what the example shows.

    Examples
    --------
    >>> import numpy as np
    >>> import pandas as pd
    >>> df = pd.DataFrame(np.random.randn(3, 3),
    ...                   columns=('a', 'b', 'c'))
    >>> df.method(1)
    21
    >>> df.method(bar=14)
    123
    """
    pass

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_016
source_url: doc/source/development/contributing_docstring.rst
source_title: pandas docstring guide
section_hint: doctest_tips

BEGIN_TEXT

Tips for getting your examples pass the doctests

General guidelines

* Import all required libraries:
  * Except pandas and NumPy (already imported as pd and np).
* Define all variables used in the example.

Random data

* Avoid using random data where possible.
* Acceptable cases:
  * probability distributions
  * large datasets difficult to construct manually
* Always use a fixed random seed.

Example

>>> np.random.seed(42)
>>> df = pd.DataFrame({'normal': np.random.normal(100, 5, 20)})

Multi-line code

* Use ... for continuation lines.

Example

>>> df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], index=['a', 'b', 'c'],
...                   columns=['A', 'B'])

Exceptions

* Show exception using full traceback header.
* Only the error name is required afterward.

Example

>>> pd.to_datetime(["712-01-01"])
Traceback (most recent call last):
OutOfBoundsDatetime: Out of bounds nanosecond timestamp: 712-01-01 00:00:00

Variable output

* Use ... for parts that may vary.

Example (incorrect)

>>> s.plot()
<matplotlib.axes._subplots.AxesSubplot at 0x7efd0c0b0690>

Example (correct)

>>> s.plot()  # doctest: +ELLIPSIS
<matplotlib.axes._subplots.AxesSubplot at ...>

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_017
source_url: doc/source/development/contributing_documentation.rst
source_title: Contributing to the documentation
section_hint: About the pandas documentation

BEGIN_TEXT

About the pandas documentation

Overview

* Documentation is written in reStructuredText.
* Built using Sphinx.
* Sphinx documentation provides guidance for advanced changes.

Structure

* pandas documentation consists of two parts:
  * docstrings in code
  * documentation in doc/ folder

Docstrings

* Provide explanations of individual functions.

Docs folder

* Contains:
  * tutorials
  * topic overviews
  * what's new
  * installation

Docstring standard

* Based on NumPy Docstring Standard.
* Follow pandas docstring guide.

Tutorials

* Use IPython directive.
* Code is executed during doc build.

Example

x = 2
x**3

Rendered output

In [1]: x = 2
In [2]: x**3
Out[2]: 8

Code execution

* Almost all examples are executed during build.
* Ensures examples stay up to date.
* Makes build more complex.

API documentation

* Located in doc/source/reference.
* Auto-generated from docstrings.

Autosummary templates

* Two templates available:

1. _templates/autosummary/class.rst
   * Generates pages for all public methods and attributes.
   * Adds Attributes and Methods sections automatically.
   * Example: DataFrame

2. _templates/autosummary/class_without_autosummary
   * Allows selecting subset of methods/attributes.
   * Requires manual Attributes and Methods sections.
   * Example: CategoricalIndex

Toctree requirement

* Every method must be included in a toctree.
* Otherwise Sphinx emits a warning.

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_018
source_url: doc/source/development/contributing_documentation.rst
source_title: Contributing to the documentation
section_hint: Docstring validation and updates

BEGIN_TEXT

Docstring validation

* Includes:
  * numpydoc checks
  * pandas-specific conventions
* Enforced during Sphinx build.
* Configured via numpydoc_validation_checks in doc/source/conf.py.

Updating a pandas docstring

* Full documentation build not always required.
* Can validate a single docstring.

Command

python doc/make.py --warnings-are-errors --no-browser --single pandas.DataFrame.mean

Guidelines

* Follow pandas docstring guide.
* Ensure examples:
  * are valid Python code
  * produce deterministic output
  * are runnable

Doctests

* Checked during validation script.
* Also tested on CI.
* Failing doctests block PR merge.

References

* See docstring examples section for guidance.

PR best practice

* Post validation output in GitHub comment.

END_TEXT
END_GUIDELINE_BLOCK

BEGIN_GUIDELINE_BLOCK
source_id: pandas_019
source_url: doc/source/development/contributing_documentation.rst
source_title: Contributing to the documentation
section_hint: Building documentation

BEGIN_TEXT

How to build the pandas documentation

Requirements

* Development environment required.

Build steps

* Navigate to doc/ directory.
* Run:

python make.py html

Output

* HTML files located in:
  * doc/build/html/

Build behavior

* First build:
  * slow (runs all examples)
* Subsequent builds:
  * faster (only changed files)

Clean build

python make.py clean
python make.py html

Troubleshooting

* If build fails:

python make.py html --num-jobs=1

Partial builds

* Build specific sections:

python make.py clean
python make.py --no-api

python make.py clean
python make.py --single development/contributing.rst

python make.py clean
python make.py --single pandas.DataFrame.join

python make.py clean
python make.py --whatsnew

Performance

* Full build: ~15 minutes
* Single section: ~15 seconds

Parallelism

* Uses available CPU cores.
* Can override:

python make.py html --num-jobs 4

Viewing output

* Open:
  * doc/build/html/index.html

Main branch documentation

* Built via CI after merge.
* Hosted online.

Previewing changes

* GitHub Actions builds documentation.
* Steps:
  * Wait for CI / Web and docs
  * Click Details
  * Download docs or website artifact

END_TEXT
END_GUIDELINE_BLOCK