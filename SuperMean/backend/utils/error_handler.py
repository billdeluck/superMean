# Directory: backend/utils/
# File: error_handler.py
# Description: Defines custom exception classes for the application.

# --- Base Application Exception ---
class SuperMeanException(Exception):
    """Base exception class for the SuperMean application."""
    def __init__(self, message="An error occurred in the SuperMean application", status_code=500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self):
        return f"{self.__class__.__name__}(status_code={self.status_code}): {self.message}"

# --- Specific Exception Types ---

class ConfigurationError(SuperMeanException):
    """Exception raised for errors in configuration loading or validation."""
    def __init__(self, message="Configuration error", missing_key=None):
        full_message = f"{message}{f': Missing key - {missing_key}' if missing_key else ''}"
        super().__init__(full_message, status_code=500)

class ModelConnectionError(SuperMeanException):
    """Exception raised for errors connecting to or interacting with LLM models."""
    def __init__(self, model_name, message="Error interacting with model"):
        full_message = f"{message}: {model_name}"
        super().__init__(full_message, status_code=503) # Service Unavailable

class SkillError(SuperMeanException):
    """Exception raised for errors during skill execution."""
    def __init__(self, skill_name, message="Error executing skill"):
        full_message = f"{message}: {skill_name}"
        super().__init__(full_message, status_code=500)

class AgentError(SuperMeanException):
    """Exception raised for errors within agent logic."""
    def __init__(self, agent_name, message="Error in agent execution"):
        full_message = f"{message}: {agent_name}"
        super().__init__(full_message, status_code=500)

class MemoryError(SuperMeanException):
    """Exception raised for errors related to memory operations."""
    def __init__(self, operation, message="Memory operation failed"):
        full_message = f"{message}: {operation}"
        super().__init__(full_message, status_code=500)

class OrchestrationError(SuperMeanException):
    """Exception raised for errors in the orchestration layer."""
    def __init__(self, component, message="Orchestration error"):
        full_message = f"{message}: {component}"
        super().__init__(full_message, status_code=500)

class APIValidationError(SuperMeanException):
    """Exception raised for API input validation errors (distinct from standard FastAPI validation)."""
    def __init__(self, detail, message="API Input Validation Error"):
        full_message = f"{message}: {detail}"
        super().__init__(full_message, status_code=422) # Unprocessable Entity

# --- FastAPI Exception Handler (Example - Integrate in api/main.py) ---
# from fastapi import FastAPI, Request
# from fastapi.responses import JSONResponse
# from backend.utils.logger import log

# def add_exception_handlers(app: FastAPI):
#     @app.exception_handler(SuperMeanException)
#     async def supermean_exception_handler(request: Request, exc: SuperMeanException):
#         log.error(f"SuperMeanException caught: {exc} for request {request.method} {request.url}")
#         return JSONResponse(
#             status_code=exc.status_code,
#             content={"detail": exc.message},
#         )

#     @app.exception_handler(Exception)
#     async def generic_exception_handler(request: Request, exc: Exception):
#         log.exception(f"Unhandled exception caught: {exc} for request {request.method} {request.url}")
#         return JSONResponse(
#             status_code=500,
#             content={"detail": "An unexpected internal server error occurred."},
#         )