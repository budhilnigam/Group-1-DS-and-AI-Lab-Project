---

repo: scikit-learn/scikit-learn

repo_name: scikit-learn

storage_type: raw_guidelines

collected_on: 2026-03-26

collector: kannan S

---



BEGIN_GUIDELINE_BLOCK

source_id: sklearn_001

source_url: https://scikit-learn.org/stable/developers/develop.html#coding-guidelines

source_title: Coding guidelines

section_hint: Coding guidelines

BEGIN_TEXT

The following are some guidelines on how new code should be written for inclusion in scikit-learn, and which may be appropriate to adopt in external projects. Of course, there are special cases and there will be exceptions to these rules. However, following these rules when submitting new code makes the review easier so new code can be integrated in less time. Uniformly formatted code makes it easier to share code ownership. The scikit-learn project tries to closely follow the official Python guidelines detailed in PEP8 that detail how code should be formatted and indented. Please read it and follow it. In addition, we add the following guidelines:

* Use underscores to separate words in non class names: n_samples rather than nsamples.
* Avoid multiple statements on one line. Prefer a line return after a control flow statement (if/for).
* Use absolute imports
* Unit tests should use imports exactly as client code would. If sklearn.foo exports a class or function that is implemented in sklearn.foo.bar.baz, the test should import it from sklearn.foo.
* Please don't use import * in any case. It is considered harmful by the official Python recommendations. It makes the code harder to read as the origin of symbols is no longer explicitly referenced, but most important, it prevents using a static analysis tool like pyflakes to automatically find bugs in scikit-learn.
* Use the [numpy docstring standard](https://numpydoc.readthedocs.io/en/latest/format.html) in all your docstrings.

END_TEXT

END_GUIDELINE_BLOCK



BEGIN_GUIDELINE_BLOCK

source_id: sklearn_002

source_url: https://scikit-learn.org/stable/developers/develop.html#instantiation

source_title: Instantiation

section_hint: Instantiation

BEGIN_TEXT

This concerns the creation of an object. The object's __init__ method might accept constants as arguments that determine the estimator's behavior (like the alpha constant in SGDClassifier). It should not, however, take the actual training data as an argument, as this is left to the fit() method.

In addition, every keyword argument accepted by __init__ should correspond to an attribute on the instance. Scikit-learn relies on this to find the relevant attributes to set on an estimator when doing model selection.

To summarize, an __init__ should look like:

    def __init__(self, param1=1, param2=2):
        self.param1 = param1
        self.param2 = param2

There should be no logic, not even input validation, and the parameters should not be changed; which also means ideally they should not be mutable objects such as lists or dictionaries. If they're mutable, they should be copied before being modified. The corresponding logic should be put where the parameters are used, typically in fit. The following is wrong:

    def __init__(self, param1=1, param2=2, param3=3):
        # WRONG: parameters should not be modified
        if param1 > 1:
            param2 += 1
        self.param1 = param1
        # WRONG: the object's attributes should have exactly the name of
        # the argument in the constructor
        self.param3 = param2

The reason for postponing the validation is that if __init__ includes input validation, then the same validation would have to be performed in set_params, which is used in algorithms like GridSearchCV.

Also it is expected that parameters with trailing _ are not to be set inside the __init__ method.

END_TEXT

END_GUIDELINE_BLOCK



BEGIN_GUIDELINE_BLOCK

source_id: sklearn_003

source_url: https://scikit-learn.org/stable/developers/develop.html#estimated-attributes

source_title: Estimated Attributes

section_hint: Estimated Attributes

BEGIN_TEXT

According to scikit-learn conventions, attributes which you'd want to expose to your users as public attributes and have been estimated or learned from the data must always have a name ending with trailing underscore, for example the coefficients of some regression estimator would be stored in a coef_ attribute after fit has been called. Similarly, attributes that you learn in the process and you'd like to store yet not expose to the user, should have a leading underscore, e.g. _intermediate_coefs. You'd need to document the first group (with a trailing underscore) as "Attributes" and no need to document the second group (with a leading underscore).

The estimated attributes are expected to be overridden when you call fit a second time.

END_TEXT

END_GUIDELINE_BLOCK


BEGIN_GUIDELINE_BLOCK

source_id: sklearn_004

source_url: https://scikit-learn.org/stable/developers/contributing.html#contribute-documentation

source_title: Contribute Documentation

section_hint: Guidelines for writing docstrings

BEGIN_TEXT

* You can use pytest to test docstrings, e.g. assuming the RandomForestClassifier docstring has been modified, the following command would test its docstring compliance:

  pytest --doctest-modules sklearn/ensemble/_forest.py -k RandomForestClassifier

* The correct order of sections is: Parameters, Returns, See Also, Notes, Examples. See the [numpydoc documentation](https://numpydoc.readthedocs.io/en/latest/format.html#sections) for information on other possible sections.
* When documenting the parameters and attributes, here is a list of some well-formatted examples

  n_clusters : int, default=3

      The number of clusters detected by the algorithm.


  some_param : {"hello", "goodbye"}, bool or int, default=True

      The parameter description goes here, which can be either a string

      literal (either `hello` or `goodbye`), a bool, or an int. The default

      value is True.


  array_parameter : {array-like, sparse matrix} of shape (n_samples, n_features) or (n_samples,)

      This parameter accepts data in either of the mentioned forms, with one

      of the mentioned shapes. The default value is `np.ones(shape=(n_samples,))`.


  list_param : list of int


  typed_ndarray : ndarray of shape (n_samples,), dtype=np.int32


  sample_weight : array-like of shape (n_samples,), default=None


  multioutput_array : ndarray of shape (n_samples, n_classes) or list of such arrays

  In general have the following in mind:

  * Use Python basic types. (bool instead of boolean)
  * Use parenthesis for defining shapes: array-like of shape (n_samples,) or array-like of shape (n_samples, n_features)
  * For strings with multiple options, use brackets: input: {'log', 'squared', 'multinomial'}
  * 1D or 2D data can be a subset of {array-like, ndarray, sparse matrix, dataframe}. Note that array-like can also be a list, while ndarray is explicitly only a numpy.ndarray.
  * Specify dataframe when "frame-like" features are being used, such as the column names.
  * When specifying the data type of a list, use of as a delimiter: list of int. When the parameter supports arrays giving details about the shape and/or data type and a list of such arrays, you can use one of array-like of shape (n_samples,) or list of such arrays.
  * When specifying the dtype of an ndarray, use e.g. dtype=np.int32 after defining the shape: ndarray of shape (n_samples,), dtype=np.int32. You can specify multiple dtype as a set: array-like of shape (n_samples,), dtype={np.float64, np.float32}. If one wants to mention arbitrary precision, use integral and floating rather than the Python dtype int and float. When both int and floating are supported, there is no need to specify the dtype.
  * When the default is None, None only needs to be specified at the end with default=None. Be sure to include in the docstring, what it means for the parameter or attribute to be None.
* Add "See Also" in docstrings for related classes/functions.
* "See Also" in docstrings should be one line per reference, with a colon and an explanation, for example:

  See Also

  SelectKBest : Select features based on the k highest scores.

  SelectFpr : Select features based on a false positive rate test.

* The "Notes" section is optional. It is meant to provide information on specific behavior of a function/class/classmethod/method.
* A Note can also be added to an attribute, but in that case it requires using the .. rubric:: Note directive.
* Add one or two **snippets** of code in "Example" section to show how it can be used. The code should be runable as is, i.e. it should include all required imports. Keep this section as brief as possible.

END_TEXT

END_GUIDELINE_BLOCK
