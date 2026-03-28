BEGIN_GUIDELINE_BLOCK

source_id: fastapi_001

source_url: https://fastapi.tiangolo.com/tutorial/body/

source_title: Request Body

section_hint: Data Validation

BEGIN_TEXT

* Declare request bodies using Pydantic models.
* Pydantic models provide automatic data validation, parsing, and documentation. They ensure that the request data matches the expected structure and types.
* Using models also enables automatic generation of JSON Schema and interactive API docs.



Example:

from fastapi import FastAPI

from pydantic import BaseModel



app = FastAPI()



class Item(BaseModel):

&#x20;   name: str

&#x20;   price: float



@app.post("/items/")

def create_item(item: Item):

&#x20;   return item

END_TEXT

END_GUIDELINE_BLOCK



BEGIN_GUIDELINE_BLOCK

source_id: fastapi_002

source_url: https://fastapi.tiangolo.com/tutorial/path-params/

source_title: Path Parameters

section_hint: API Design

BEGIN_TEXT

* Declare path parameters using Python type hints.
* FastAPI uses type hints to validate and convert path parameters automatically. Invalid data will generate clear validation errors.
* Using types also improves editor support and automatic documentation.



Example:

from fastapi import FastAPI



app = FastAPI()



@app.get("/items/{item_id}")

def read_item(item_id: int):

&#x20;   return {"item_id": item_id}

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_003

source_url: https://fastapi.tiangolo.com/tutorial/query-params/

source_title: Query Parameters

section_hint: API Design

BEGIN_TEXT

* Use function parameters to declare query parameters.
* Default values make parameters optional, while type hints define validation rules. FastAPI automatically handles parsing and validation.
* Query parameters are included in the generated documentation with their types and defaults.



Example:

from fastapi import FastAPI



app = FastAPI()



@app.get("/items/")

def read_items(skip: int = 0, limit: int = 10):

&#x20;   return {"skip": skip, "limit": limit}

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_004

source_url: https://fastapi.tiangolo.com/tutorial/dependencies/

source_title: Dependencies

section_hint: API Design

BEGIN_TEXT

* Use the dependency injection system to share logic across endpoints.
* Dependencies are declared as standard Python functions and can be reused in multiple path operations.
* This allows separation of concerns and avoids repeating code such as authentication, database access, or configuration.



Example:

from fastapi import Depends, FastAPI



app = FastAPI()



def common_parameters(q: str = None):

&#x20;   return {"q": q}



@app.get("/items/")

def read_items(commons: dict = Depends(common_parameters)):

&#x20;   return commons

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_005

source_url: https://fastapi.tiangolo.com/tutorial/response-model/

source_title: Response Model

section_hint: Data Validation

BEGIN_TEXT

* Use response_model to define the structure of responses.
* FastAPI will validate and filter the output data according to the defined model.
* This ensures that only the declared fields are returned and improves data consistency and security.



Example:

from fastapi import FastAPI

from pydantic import BaseModel



app = FastAPI()



class Item(BaseModel):

&#x20;   name: str

&#x20;   price: float



@app.get("/items/", response_model=Item)

def read_item():

&#x20;   return {"name": "Item", "price": 10.5}

END_TEXT

END_GUIDELINE_BLOCK



BEGIN_GUIDELINE_BLOCK

source_id: fastapi_006

source_url: https://fastapi.tiangolo.com/tutorial/handling-errors/

source_title: Handling Errors

section_hint: Error Handling

BEGIN_TEXT

* Raise HTTPException to return errors from path operations.
* HTTPException allows specifying status codes and error details in a consistent format.
* FastAPI automatically converts these exceptions into proper HTTP responses.



Example:

from fastapi import FastAPI, HTTPException



app = FastAPI()



@app.get("/items/{item_id}")

def read_item(item_id: int):

&#x20;   if item_id == 0:

&#x20;       raise HTTPException(status_code=404, detail="Item not found")

&#x20;   return {"item_id": item_id}

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_007

source_url: https://fastapi.tiangolo.com/async/

source_title: Async and Await

section_hint: Python Style

BEGIN_TEXT

* Use async def for path operations that perform I/O operations.
* Async functions allow FastAPI to handle multiple requests efficiently without blocking.
* Standard def functions can still be used for synchronous code.



Example:

from fastapi import FastAPI



app = FastAPI()



@app.get("/")

async def read_root():

&#x20;   return {"message": "Hello World"}

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_008

source_url: https://fastapi.tiangolo.com/tutorial/body-nested-models/

source_title: Nested Models

section_hint: Data Validation

BEGIN_TEXT

* Use nested Pydantic models to represent complex data structures.
* Models can contain other models, enabling validation of deeply nested JSON data.
* This provides clear structure and automatic validation for complex request bodies.



Example:

from pydantic import BaseModel



class Item(BaseModel):

&#x20;   name: str



class User(BaseModel):

&#x20;   username: str

&#x20;   item: Item

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_009

source_url: https://fastapi.tiangolo.com/tutorial/body-fields/

source_title: Body Fields

section_hint: Data Validation

BEGIN_TEXT

* Use Field to add validation and metadata to model attributes.
* Field allows defining constraints such as minimum length, maximum length, and descriptions.
* These constraints are enforced during validation and included in the API documentation.



Example:

from pydantic import BaseModel, Field



class Item(BaseModel):

&#x20;   name: str = Field(min_length=3, max_length=50)

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_010

source_url: https://fastapi.tiangolo.com/tutorial/background-tasks/

source_title: Background Tasks

section_hint: API Design

BEGIN_TEXT

* Use BackgroundTasks to run operations after returning a response.
* This is useful for tasks such as sending emails or processing data without blocking the request.
* Background tasks are executed after the response is sent to the client.



Example:

from fastapi import BackgroundTasks, FastAPI



app = FastAPI()



def write_log(message: str):

&#x20;   with open("log.txt", "a") as f:

&#x20;       f.write(message)



@app.post("/send/")

def send(background_tasks: BackgroundTasks):

&#x20;   background_tasks.add_task(write_log, "Task executed\\n")

&#x20;   return {"message": "Task scheduled"}

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_011

source_url: https://fastapi.tiangolo.com/tutorial/path-operation-configuration/

source_title: Path Operation Configuration

section_hint: API Design

BEGIN_TEXT

* Use path operation decorators to define metadata such as summary, description, and tags.
* These parameters improve the generated OpenAPI schema and interactive documentation.
* Providing clear metadata helps users understand the purpose and usage of each endpoint.



END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_012

source_url: https://fastapi.tiangolo.com/tutorial/path-operation-configuration/

source_title: Tags

section_hint: API Design

BEGIN_TEXT

* Use tags to group related path operations.
* Tags are used in the automatically generated documentation to organize endpoints into logical sections.
* This improves navigation and usability of the API documentation.



Example:

@app.get("/items/", tags=\["items"])

def read_items():

&#x20;   return \[]

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_013

source_url: https://fastapi.tiangolo.com/tutorial/status-codes/

source_title: Status Codes

section_hint: API Design

BEGIN_TEXT

* Use the status_code parameter to define the HTTP status returned by a path operation.
* This allows explicit control over the response status and improves API clarity.



Example:

from fastapi import FastAPI, status



app = FastAPI()



@app.post("/items/", status_code=status.HTTP_201_CREATED)

def create_item():

&#x20;   return {"message": "created"}

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_014

source_url: https://fastapi.tiangolo.com/tutorial/response-status-code/

source_title: Response Status Code

section_hint: API Design

BEGIN_TEXT

* Return appropriate HTTP status codes for each operation.
* Different operations such as creation, deletion, or errors should return corresponding status codes.
* This helps clients correctly interpret the result of a request.



END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_015

source_url: https://fastapi.tiangolo.com/tutorial/request-forms/

source_title: Form Data

section_hint: Data Validation

BEGIN_TEXT

* Use Form to declare form data parameters.
* Form data is handled similarly to query and body parameters, with validation based on type hints.



Example:

from fastapi import FastAPI, Form



app = FastAPI()



@app.post("/login/")

def login(username: str = Form(...), password: str = Form(...)):

&#x20;   return {"username": username}

END_TEXT

END_GUIDELINE_BLOCK







BEGIN_GUIDELINE_BLOCK

source_id: fastapi_016

source_url: https://fastapi.tiangolo.com/tutorial/request-files/

source_title: File Uploads

section_hint: API Design

BEGIN_TEXT

* Use UploadFile to handle file uploads.
* UploadFile provides file-like objects and supports efficient handling of large files.



Example:

from fastapi import FastAPI, UploadFile



app = FastAPI()



@app.post("/upload/")

def upload(file: UploadFile):

&#x20;   return {"filename": file.filename}

END_TEXT

END_GUIDELINE_BLOCK







BEGIN_GUIDELINE_BLOCK

source_id: fastapi_017

source_url: https://fastapi.tiangolo.com/tutorial/request-files/

source_title: Multiple File Uploads

section_hint: API Design

BEGIN_TEXT

* Use lists of UploadFile to accept multiple files.
* FastAPI automatically parses multiple uploaded files into a list.



Example:

from typing import List

from fastapi import UploadFile



@app.post("/files/")

def upload_files(files: List\[UploadFile]):

&#x20;   return {"count": len(files)}

END_TEXT

END_GUIDELINE_BLOCK





BEGIN_GUIDELINE_BLOCK

source_id: fastapi_018

source_url: https://fastapi.tiangolo.com/tutorial/first-steps/

source_title: Automatic Docs

section_hint: API Design

BEGIN_TEXT

* FastAPI automatically generates interactive API documentation.
* The documentation is available at /docs and /redoc endpoints.
* It is based on the OpenAPI standard and reflects the declared types and models.



END_TEXT

END_GUIDELINE_BLOCK











