---

repo: scikit-learn/scikit-learn

repo_name: scikit-learn

storage_type: raw_guidelines

collected_on: 2026-03-26

collector: kannan S

---



BEGIN_GUIDELINE_BLOCK

source_id: sklearn_001

source_url: https://scikit-learn.org/stable/developers/contributing.html#contribute-documentation

source_title: Contribute Documentation

section_hint: Guidelines for writing docstrings

BEGIN_TEXT

* You can use pytest to test docstrings, e.g. assuming the RandomForestClassifier docstring has been modified, the following command would test its docstring compliance:

  pytest --doctest-modules sklearn/ensemble/_forest.py -k RandomForestClassifier

* The correct order of sections is: Parameters, Returns, See Also, Notes, Examples. See the [numpydoc documentation](https://numpydoc.readthedocs.io/en/latest/format.html#sections) for information on other possible sections.  
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

  * Use Python basic types. (bool instead of boolean)  
  * Use parenthesis for defining shapes: array-like of shape (n_samples,) or array-like of shape (n_samples, n_features)  
  * For strings with multiple options, use brackets: input: {'log', 'squared', 'multinomial'}  
  * 1D or 2D data can be a subset of {array-like, ndarray, sparse matrix, dataframe}. Note that array-like can also be a list, while ndarray is explicitly only a numpy.ndarray.  
  * Specify dataframe when “frame-like” features are being used, such as the column names.  
  * When specifying the data type of a list, use of as a delimiter: list of int. When the parameter supports arrays giving details about the shape and/or data type and a list of such arrays, you can use one of array-like of shape (n_samples,) or list of such arrays.  
  * When specifying the dtype of an ndarray, use e.g. dtype=np.int32 after defining the shape: ndarray of shape (n_samples,), dtype=np.int32. You can specify multiple dtype as a set: array-like of shape (n_samples,), dtype={np.float64, np.float32}. If one wants to mention arbitrary precision, use integral and floating rather than the Python dtype int and float. When both int and floating are supported, there is no need to specify the dtype.  
  * When the default is None, None only needs to be specified at the end with default=None. Be sure to include in the docstring, what it means for the parameter or attribute to be None.  
* Add “See Also” in docstrings for related classes/functions.  
* “See Also” in docstrings should be one line per reference, with a colon and an explanation, for example:

  See Also

  SelectKBest : Select features based on the k highest scores.

  SelectFpr : Select features based on a false positive rate test.

* The “Notes” section is optional. It is meant to provide information on specific behavior of a function/class/classmethod/method.  
* A Note can also be added to an attribute, but in that case it requires using the .. rubric:: Note directive.  
* Add one or two **snippets** of code in “Example” section to show how it can be used. The code should be runable as is, i.e. it should include all required imports. Keep this section as brief as possible.

END_TEXT

END_GUIDELINE_BLOCK