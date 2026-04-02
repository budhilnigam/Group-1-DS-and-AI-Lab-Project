"""
exceptions.py

Custom exception classes and handlers for FastAPI projects.
Provides: NotFoundError, ForbiddenError, ValidationError, and their handler registration.
"""

from typing import Any
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_403_FORBIDDEN,
    HTTP_422_UNPROCESSABLE_ENTITY,
)


class NotFoundError(Exception):
  """
  Exception raised when a requested resource is not found.
  """

  def __init__(self, detail: str = "Resource not found") -> None:
    self.detail = detail
    super().__init__(self.detail)


class ForbiddenError(Exception):
  """
  Exception raised when access is forbidden.
  """

  def __init__(self, detail: str = "Access forbidden") -> None:
    self.detail = detail
    super().__init__(self.detail)


class ValidationError(Exception):
  """
  Exception raised when input validation fails.
  """

  def __init__(self, detail: str = "Validation failed", errors: Any = None) -> None:
    self.detail = detail
    self.errors = errors
    super().__init__(self.detail)


async def notFoundErrorHandler(request: Request, exc: NotFoundError) -> JSONResponse:
  """
  Handler for NotFoundError exceptions.
  Returns 404 response with error detail.
  """
  return JSONResponse(
    status_code=HTTP_404_NOT_FOUND,
    content={
      "error": "not_found",
      "detail": exc.detail,
      "path": str(request.url),
    },
  )


async def forbiddenErrorHandler(request: Request, exc: ForbiddenError) -> JSONResponse:
  """
  Handler for ForbiddenError exceptions.
  Returns 403 response with error detail.
  """
  return JSONResponse(
    status_code=HTTP_403_FORBIDDEN,
    content={
      "error": "forbidden",
      "detail": exc.detail,
      "path": str(request.url),
    },
  )


async def validationErrorHandler(request: Request, exc: ValidationError) -> JSONResponse:
  """
  Handler for ValidationError exceptions.
  Returns 422 response with error detail and optional errors.
  """
  content = {
    "error": "validation_error",
    "detail": exc.detail,
    "path": str(request.url),
  }
  if exc.errors is not None:
    content["errors"] = exc.errors
  return JSONResponse(
    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    content=content,
  )


def registerExceptionHandlers(app: FastAPI) -> None:
  """
  Register custom exception handlers to the FastAPI app.
  """
  app.add_exception_handler(NotFoundError, notFoundErrorHandler)
  app.add_exception_handler(ForbiddenError, forbiddenErrorHandler)
  app.add_exception_handler(ValidationError, validationErrorHandler)