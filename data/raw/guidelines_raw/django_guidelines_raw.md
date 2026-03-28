\---

repo: django/django

repo_name: Django

storage_type: raw_guidelines

collected_on: 2026-03-21

collector: team_member_name

\---

 

BEGIN_GUIDELINE_BLOCK

source_id: django_001

source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/

source_title: Python Coding Style

section_hint: Python style

BEGIN_TEXT

* All files should be formatted using the [black](https://pypi.org/project/black/) auto-formatter. This will be run by **pre-commit** if that is configured.  
* The project repository includes an **.editorconfig** file. We recommend using a text editor with [EditorConfig](https://editorconfig.org/) support to avoid indentation and whitespace issues. The Python files use 4 spaces for indentation and the HTML files use 2 spaces.  
* Unless otherwise specified, follow [**PEP 8**](https://peps.python.org/pep-0008/).  
  Use [flake8](https://pypi.org/project/flake8/) to check for problems in this area. Note that our **.flake8** file excludes some errors that we don’t consider as gross violations. Remember that [**PEP 8**](https://peps.python.org/pep-0008/) is only a guide, so respect the style of the surrounding code as a primary goal.  
  An exception to [**PEP 8**](https://peps.python.org/pep-0008/) is our rules on line lengths. We allow up to 88 characters in code, as this is the line length used by **black**. Documentation, comments, and docstrings should be wrapped at 79 characters. These limits are checked when **flake8** is run.  
* String variable interpolation may use [%-formatting](https://docs.python.org/3/library/stdtypes.html#old-string-formatting), [f-strings](https://docs.python.org/3/reference/lexical_analysis.html#f-strings), or [**str.format()**](https://docs.python.org/3/library/stdtypes.html#str.format) as appropriate, with the goal of maximizing code readability.  
  Final judgments of readability are left to the Merger’s discretion. As a guide, f-strings should use only plain variable and property access, with prior local variable assignment for more complex cases:  
  *\# Allowed*  
  f"hello **{**user**}**"  
  f"hello **{**user**.**name**}**"  
  f"hello **{**self**.**user**.**name**}**"  
     
  *\# Disallowed*  
  f"hello **{**get_user()**}**"  
  f"you are **{**user**.**age **\*** 365.25**}** days old"  
     
  *\# Allowed with local variable assignment*  
  user **\=** get_user()  
  f"hello **{**user**}**"  
  user_days_old **\=** user**.**age **\*** 365.25  
  f"you are **{**user_days_old**}** days old"  
  f-strings should not be used for any string that may require translation, including error and logging messages. In general **format()** is more verbose, so the other formatting methods are preferred.  
  Don’t waste time doing unrelated refactoring of existing code to adjust the formatting method.  
* Avoid use of “we” in comments, e.g. “Loop over” rather than “We loop over”.  
* Use underscores, not camelCase, for variable, function and method names (i.e. **poll.get_unique_voters()**, not **poll.getUniqueVoters()**).  
* Use **InitialCaps** for class names (or for factory functions that return classes).  
* In docstrings, follow the style of existing docstrings and [**PEP 257**](https://peps.python.org/pep-0257/).  
* In tests, use [**assertRaisesMessage()**](https://docs.djangoproject.com/en/dev/topics/testing/tools/#django.test.SimpleTestCase.assertRaisesMessage) and [**assertWarnsMessage()**](https://docs.djangoproject.com/en/dev/topics/testing/tools/#django.test.SimpleTestCase.assertWarnsMessage) instead of [**assertRaises()**](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertRaises) and [**assertWarns()**](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertWarns) so you can check the exception or warning message. Use [**assertRaisesRegex()**](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertRaisesRegex) and [**assertWarnsRegex()**](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertWarnsRegex) only if you need regular expression matching.  
  Use [**assertIs(…, True/False)**](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertIs) for testing boolean values, rather than [**assertTrue()**](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertTrue) and [**assertFalse()**](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertFalse), so you can check the actual boolean value, not the truthiness of the expression.  
* In test docstrings, state the expected behavior that each test demonstrates. Don’t include preambles such as “Tests that” or “Ensures that”.  
  Reserve ticket references for obscure issues where the ticket has additional details that can’t be easily described in docstrings or comments. Include the ticket number at the end of a sentence like this:  
  **def** **test_foo**():  
  	*"""*  
  	*A test docstring looks like this (\#123456).*  
  	*"""*  
  	**...**  
* Where applicable, use unpacking generalizations compliant with [**PEP 448**](https://peps.python.org/pep-0448/), such as merging mappings (**{x, y}**) or sequences (**[a, b]**). This improves performance, readability, and maintainability while reducing errors.

END_TEXT

END_GUIDELINE_BLOCK

 

BEGIN_GUIDELINE_BLOCK

source_id: django_002

source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/

source_title: Python Coding Style

section_hint: Imports

BEGIN_TEXT

* Use [isort](https://pypi.org/project/isort/) to automate import sorting using the guidelines below.  
  Quick start:  
  **\$** python -m pip install "isort >= 7.0.0"  
  **\$** isort .  
  This runs **isort** recursively from your current directory, modifying any files that don’t conform to the guidelines. If you need to have imports out of order (to avoid a circular import, for example) use a comment like this:  
  **import** **module**  *\# isort:skip*  
* Put imports in these groups: future, standard library, third-party libraries, other Django components, local Django component, try/excepts. Sort lines in each group alphabetically by the full module name. Place all **import module** statements before **from module import objects** in each section. Use absolute imports for other Django components and a one-dot relative import (**from .foo import Bar**) for local components. Avoid multi-dot relative imports.  
* On each line, alphabetize the items with the upper case items grouped before the lowercase items.  
* Break long lines using parentheses and indent continuation lines by 4 spaces. Include a trailing comma after the last import and put the closing parenthesis on its own line.  
  Use a single blank line between the last import and any module level code, and use two blank lines above the first function or class.  
  For example (comments are for explanatory purposes only):  
  django/contrib/admin/example.py[**¶**](https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/#id1)  
  *\# future*  
  **from** **__future__** **import** unicode_literals  
     
  *\# standard library*  
  **import** **json**  
  **from** **itertools** **import** chain  
     
  *\# third-party*  
  **import** **bcrypt**  
     
  *\# Django*  
  **from** **django.http** **import** Http404  
  **from** **django.http.response** **import** (  
  	Http404,  
  	HttpResponse,  
  	HttpResponseNotAllowed,  
  	StreamingHttpResponse,  
  	cookie,  
  )  
     
  *\# local Django*  
  **from** **.models** **import** LogEntry  
     
  *\# try/except*  
  **try**:  
  	**import** **yaml**  
  **except** **ImportError**:  
  	yaml **\=** **None**  
     
  CONSTANT **\=** "foo"  
     
     
  **class** **Example**: **...**  
* Use convenience imports whenever available. For example, do this  
  · 	**from** **django.views** **import** View  
  instead of:  
  **from** **django.views.generic.base** **import** View

END_TEXT

END_GUIDELINE_BLOCK

 

BEGIN_GUIDELINE_BLOCK

source_id: django_003

source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/

source_title: Python Coding Style

source_hint: Template style

BEGIN_TEXT

Follow the below rules in Django template code.

* **{% extends %}** should be the first non-comment line.  
  Do this:  
  ***{%*** **extends** "base.html" ***%}***  
     
  ***{%*** **block** content ***%}***  
    \<**h1** class**\=**"font-semibold text-xl"\>  
  	***{{*** pages.title ***}}***  
    \</**h1**\>  
  ***{%*** **endblock** content ***%}***  
  Or this:  
  *{\# This is a comment \#}*  
  ***{%*** **extends** "base.html" ***%}***  
     
  ***{%*** **block** content ***%}***  
    \<**h1** class**\=**"font-semibold text-xl"\>  
  	***{{*** pages.title ***}}***  
    \</**h1**\>  
  ***{%*** **endblock** content ***%}***  
  Don’t do this:  
  ***{%*** **load** i18n ***%}***  
  ***{%*** **extends** "base.html" ***%}***  
     
  ***{%*** **block** content ***%}***  
    \<**h1** class**\=**"font-semibold text-xl"\>  
  	***{{*** pages.title ***}}***  
    \</**h1**\>  
  ***{%*** **endblock** content ***%}***  
* Put exactly one space between **{{**, variable contents, and **}}**.  
  Do this:  
  ***{{*** user ***}}***  
  Don’t do this:  
  ***{{***user***}}***  
* In **{% load ... %}**, list libraries in alphabetical order.  
  Do this:  
  ***{%*** **load** i18n l10 tz ***%}***  
  Don’t do this:  
  ***{%*** **load** l10 i18n tz ***%}***  
* Put exactly one space between **{%**, tag contents, and **%}**.  
  Do this:  
  ***{%*** **load** humanize ***%}***  
  Don’t do this:  
  ***{%*****load** humanize***%}***  
* Put the **{% block %}** tag name in the **{% endblock %}** tag if it is not on the same line.  
  Do this:  
  ***{%*** **block** header ***%}***  
     
    Code goes here  
     
  ***{%*** **endblock** header ***%}***  
  Don’t do this:  
  ***{%*** **block** header ***%}***  
     
    Code goes here  
     
  ***{%*** **endblock** ***%}***  
* Inside curly braces, separate tokens by single spaces, except for around the **.** for attribute access and the **|** for a filter.  
  Do this:  
  ***{%*** **if** user.name**|lower** **\==** "admin" ***%}***  
  Don’t do this:  
  ***{%*** **if** user . name **|** **lower**  **\==**  "admin" ***%}***  
     
  ***{{*** user.name **|** **upper** ***}}***  
* Within a template using **{% extends %}**, avoid indenting top-level **{% block %}** tags.  
  Do this:  
  ***{%*** **extends** "base.html" ***%}***  
     
  ***{%*** **block** content ***%}***  
  Don’t do this:  
  ***{%*** **extends** "base.html" ***%}***  
     
    ***{%*** **block** content ***%}***  
    ...

END_TEXT

END_GUIDELINE_BLOCK

 

BEGIN_GUIDELINE_BLOCK

source_id: django_004

source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/

source_title: Python Coding Style

source_hint: View style

BEGIN_TEXT

* In Django views, the first parameter in a view function should be called **request**.  
  Do this:  
  **def** **my_view**(request, foo): **...**  
  Don’t do this:  
  **def** **my_view**(req, foo): **...**

END_TEXT

END_GUIDELINE_BLOCK

 

BEGIN_GUIDELINE_BLOCK

source_id: django_005

source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/

source_title: Python Coding Style

source_hint: Model style

BEGIN_TEXT

* Field names should be all lowercase, using underscores instead of camelCase.  
  Do this:  
  **class** **Person**(models**.**Model):  
  	first_name **\=** models**.**CharField(max_length**\=**20)  
  	last_name **\=** models**.**CharField(max_length**\=**40)  
  Don’t do this:  
  **class** **Person**(models**.**Model):  
      FirstName **\=** models**.**CharField(max_length**\=**20)  
  	Last_Name **\=** models**.**CharField(max_length**\=**40)  
* The **class Meta** should appear *after* the fields are defined, with a single blank line separating the fields and the class definition.  
  Do this:  
  **class** **Person**(models**.**Model):  
  	first_name **\=** models**.**CharField(max_length**\=**20)  
  	last_name **\=** models**.**CharField(max_length**\=**40)  
     
  	**class** **Meta**:  
     	 verbose_name_plural **\=** "people"  
  Don’t do this:  
  **class** **Person**(models**.**Model):  
  	**class** **Meta**:  
      	verbose_name_plural **\=** "people"  
     
  	first_name **\=** models**.**CharField(max_length**\=**20)  
  	last_name **\=** models**.**CharField(max_length**\=**40)  
* The order of model inner classes and standard methods should be as follows (noting that these are not all required):  
  * All database fields  
  * Custom manager attributes  
  * **class Meta**  
  * **def __str__()** and other Python magic methods  
  * **def save()**  
  * **def get_absolute_url()**  
  * Any custom methods  
* If **choices** is defined for a given model field, define each choice as a mapping, with an all-uppercase name as a class attribute on the model. Example:  
  · 	**class** **MyModel**(models**.**Model):  
  · 	    DIRECTION_UP **\=** "U"  
  · 	    DIRECTION_DOWN **\=** "D"  
  · 	    DIRECTION_CHOICES **\=** {  
  · 	        DIRECTION_UP: "Up",  
  · 	        DIRECTION_DOWN: "Down",  
  · 	    }  
  Alternatively, consider using [Enumeration types](https://docs.djangoproject.com/en/dev/ref/models/fields/#field-choices-enum-types):  
  **class** **MyModel**(models**.**Model):  
  	**class** **Direction**(models**.**TextChoices):  
      	UP **\=** "U", "Up"  
      	DOWN **\=** "D", "Down"

END_TEXT

END_GUIDELINE_BLOCK

 

BEGIN_GUIDELINE_BLOCK

source_id: django_006

source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/

source_title: Python Coding Style

source_hint: Use of **django.conf.settings**

BEGIN_TEXT

Modules should not in general use settings stored in **django.conf.settings** at the top level (i.e. evaluated when the module is imported). The explanation for this is as follows:

Manual configuration of settings (i.e. not relying on the [**DJANGO_SETTINGS_MODULE**](https://docs.djangoproject.com/en/dev/topics/settings/#envvar-DJANGO_SETTINGS_MODULE) environment variable) is allowed and possible as follows:

**from** **django.conf** **import** settings

 

settings**.**configure({}, SOME_SETTING**\=**"foo")

However, if any setting is accessed before the **settings.configure** line, this will not work. (Internally, **settings** is a **LazyObject** which configures itself automatically when the settings are accessed if it has not already been configured).

So, if there is a module containing some code as follows:

**from** **django.conf** **import** settings

**from** **django.urls** **import** get_callable

 

default_foo_view **\=** get_callable(settings**.**FOO_VIEW)

…then importing this module will cause the settings object to be configured. That means that the ability for third parties to import the module at the top level is incompatible with the ability to configure the settings object manually, or makes it very difficult in some circumstances.

Instead of the above code, a level of laziness or indirection must be used, such as **django.utils.functional.LazyObject**, **django.utils.functional.lazy()** or **lambda**.

END_TEXT

END_GUIDELINE_BLOCK

 

BEGIN_GUIDELINE_BLOCK

source_id: django_007

source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/javascript/

source_title: Javascript Coding Style

source_hint: Code style

BEGIN_TEXT

* Please conform to the indentation style dictated in the **.editorconfig** file. We recommend using a text editor with [EditorConfig](https://editorconfig.org/) support to avoid indentation and whitespace issues. Most of the JavaScript files use 4 spaces for indentation, but there are some exceptions.  
* When naming variables, use **camelCase** instead of **underscore_case**. Different JavaScript files sometimes use a different code style. Please try to conform to the code style of each file.  
* Use the [ESLint](https://eslint.org/) code linter to check your code for bugs and style errors. ESLint will be run when you run the JavaScript tests. We also recommended installing a ESLint plugin in your text editor.  
* Where possible, write code that will work even if the page structure is later changed with JavaScript. For instance, when binding a click handler, use **$('body').on('click', selector, func)** instead of **$(selector).click(func)**. This makes it easier for projects to extend Django’s default behavior with JavaScript.

END_TEXT

END_GUIDELINE_BLOCK

 

BEGIN_GUIDELINE_BLOCK

source_id: django_008

source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/javascript/

source_title: Javascript Coding Style

source_hint: Javascript patches

BEGIN_TEXT

Django’s admin system leverages the jQuery framework to increase the capabilities of the admin interface. In conjunction, there is an emphasis on admin JavaScript performance and minimizing overall admin media file size.

END_TEXT

END_GUIDELINE_BLOCK

 

BEGIN_GUIDELINE_BLOCK

source_id: django_009

source_url: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/javascript/

source_title: Javascript Coding Style

source_hint: Javascript Tests

BEGIN_TEXT

Django’s JavaScript tests can be run in a browser or from the command line. The tests are located in a top level [js_tests](https://github.com/django/django/blob/main/js_tests) directory.

**Writing tests**

Django’s JavaScript tests use [QUnit](https://qunitjs.com/). Here is an example test module:

QUnit.module('magicTricks', {

	beforeEach: function() {

    	const $ = django.jQuery;

    	$('#qunit-fixture').append('<button class="button"\></button>');

	}

});

 

QUnit.test('removeOnClick removes button on click', **function**(assert) {

	const $ = django.jQuery;

	removeOnClick('.button');

	assert.equal($('.button').length, 1);

	$('.button').click();

	assert.equal($('.button').length, 0);

});

 

QUnit.test('copyOnClick adds button on click', **function**(assert) {

	const $ = django.jQuery;

	copyOnClick('.button');

	assert.equal($('.button').length, 1);

	$('.button').click();

	assert.equal($('.button').length, 2);

});

**Running tests**

The JavaScript tests may be run from a web browser or from the command line.

#### Testing from a web browser

To run the tests from a web browser, open up [js_tests/tests.html](https://github.com/django/django/blob/main/js_tests/tests.html) in your browser.

To measure code coverage when running the tests, you need to view that file over HTTP. To view code coverage:

* Execute **python \-m http.server** from the root directory (not from inside **js_tests**).

* Open [http://localhost:8000/js_tests/tests.html](http://localhost:8000/js_tests/tests.html) in your web browser.

#### Testing from the command line

To run the tests from the command line, you need to have [Node.js](https://nodejs.org/) installed.

After installing **Node.js**, install the JavaScript test dependencies by running the following from the root of your Django checkout:

**$** npm install

Then run the tests with:

**$** npm test

 

