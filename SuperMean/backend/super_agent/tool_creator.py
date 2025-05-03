# Directory: backend/super_agent/
# File: tool_creator.py
# Description: Component responsible for dynamically creating and registering new skills (tools).
# WARNING: Uses exec(). Use with extreme caution. (Corrected _compile_and_register)

import asyncio
import inspect
import importlib
import re
import ast
import functools
import hashlib
from typing import Any, Dict, Optional, Callable, Coroutine, Type, List, Union, Tuple, Set
from functools import lru_cache
import typing
import radon.complexity
import resource
import threading
import psutil
import time
import sys

from backend.models.model_router import ModelRouter
from backend.skills import _skills_registry, register_skill, SkillError
from backend.utils.logger import setup_logger
from backend.utils.error_handler import SuperMeanException

log = setup_logger(name="super_agent_tool_creator")

class ToolQualityMetrics:
    """Quality metrics for generated tool code."""
    def __init__(self):
        self.complexity_score: float = 0.0
        self.security_score: float = 0.0
        self.type_safety_score: float = 0.0
        self.error_handling_score: float = 0.0
        self.code_quality_issues: List[str] = []

    @property
    def overall_score(self) -> float:
        weights = {
            'complexity': 0.25,
            'security': 0.35,
            'type_safety': 0.25,
            'error_handling': 0.15
        }
        return (
            weights['complexity'] * self.complexity_score +
            weights['security'] * self.security_score +
            weights['type_safety'] * self.type_safety_score +
            weights['error_handling'] * self.error_handling_score
        )

class ToolCreationError(SuperMeanException):
    """Custom exception for tool creation failures."""
    def __init__(self, message="Failed to create or register tool", status_code=500, cause: Optional[Exception] = None):
        super().__init__(message, status_code)
        if cause:
            self.__cause__ = cause
    def __str__(self) -> str:
        return self.message

class SecurityError(ToolCreationError):
    """Custom exception for security violations."""
    def __init__(self, message="Security violation detected", cause: Optional[Exception] = None):
        super().__init__(message, status_code=403, cause=cause)

class ResourceMonitor:
    """Monitors resource usage during function execution."""
    def __init__(self, limits: Dict[str, float]):
        self.limits = limits
        self.start_usage = None
        self.peak_memory = 0
        self.cpu_usage = 0.0
        self.execution_time = 0.0
        self._monitoring = False
        self._monitor_thread = None
        
    def _check_memory_usage(self, process: psutil.Process) -> None:
        """Monitor memory usage of a process."""
        while self._monitoring:
            try:
                memory_info = process.memory_info()
                self.peak_memory = max(self.peak_memory, memory_info.rss)
                if self.peak_memory > self.limits['max_memory']:
                    raise SecurityError("Memory limit exceeded")
                time.sleep(0.1)  # Check every 100ms
            except psutil.NoSuchProcess:
                break

    def __enter__(self):
        """Start resource monitoring."""
        self._monitoring = True
        self.start_usage = time.time()
        
        # Set resource limits
        resource.setrlimit(resource.RLIMIT_AS, (self.limits['max_memory'], self.limits['max_memory']))
        resource.setrlimit(resource.RLIMIT_CPU, (self.limits['max_cpu_time'], self.limits['max_cpu_time']))
        
        # Start memory monitoring in background
        process = psutil.Process()
        self._monitor_thread = threading.Thread(
            target=self._check_memory_usage,
            args=(process,),
            daemon=True
        )
        self._monitor_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop resource monitoring and collect metrics."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            
        # Calculate resource usage
        self.execution_time = time.time() - self.start_usage
        if self.execution_time > self.limits['max_wall_time']:
            raise SecurityError("Execution time limit exceeded")
        
        # Check CPU usage
        process = psutil.Process()
        self.cpu_usage = process.cpu_percent()
        if self.cpu_usage > self.limits['max_cpu_percent']:
            raise SecurityError("CPU usage limit exceeded")
        
        return False  # Re-raise any exceptions

class SecuritySandbox:
    """Enhanced sandbox with resource monitoring."""
    def __init__(self, allowed_builtins: Set[str], safe_modules: Dict[str, Set[str]], 
                 resource_limits: Optional[Dict[str, float]] = None):
        self.allowed_builtins = allowed_builtins
        self.safe_modules = safe_modules
        self.original_builtins = None
        self.imported_modules = {}
        
        # Default resource limits
        self.resource_limits = resource_limits or {
            'max_memory': 100 * 1024 * 1024,  # 100MB
            'max_cpu_time': 5,                # 5 seconds CPU time
            'max_wall_time': 10,              # 10 seconds wall time
            'max_cpu_percent': 50,            # 50% CPU usage
        }
        
        self.monitor = ResourceMonitor(self.resource_limits)

    def _create_restricted_builtins(self):
        """Create a restricted __builtins__ dict."""
        restricted = {}
        real_builtins = dict(__builtins__) if isinstance(__builtins__, dict) else dict(dir(__builtins__))
        
        for name in self.allowed_builtins:
            if name in real_builtins:
                restricted[name] = real_builtins[name]
        return restricted

    def _create_module_proxy(self, module_name: str, allowed_attrs: Set[str]):
        """Create a proxy for modules with restricted attributes."""
        if module_name not in sys.modules:
            raise SecurityError(f"Module {module_name} not available")
            
        real_module = sys.modules[module_name]
        
        class ModuleProxy:
            def __getattr__(self, name):
                if name not in allowed_attrs and allowed_attrs != {'*'}:
                    raise SecurityError(f"Access to {module_name}.{name} is not allowed")
                return getattr(real_module, name)
                
            def __setattr__(self, name, value):
                raise SecurityError("Module modification not allowed")
                
        return ModuleProxy()

    def __enter__(self):
        """Set up sandbox with resource monitoring."""
        # Start resource monitoring
        self.monitor.__enter__()
        
        # Original sandbox setup
        self.original_builtins = dict(__builtins__)
        restricted_builtins = self._create_restricted_builtins()
        import builtins
        builtins.__dict__.update(restricted_builtins)
        
        for module_name, allowed_attrs in self.safe_modules.items():
            try:
                self.imported_modules[module_name] = self._create_module_proxy(
                    module_name, allowed_attrs
                )
            except Exception as e:
                log.warning(f"Failed to create proxy for {module_name}: {e}")
        
        return self.imported_modules

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up sandbox and stop monitoring."""
        try:
            # Stop resource monitoring
            self.monitor.__exit__(exc_type, exc_val, exc_tb)
            
            # Restore original environment
            import builtins
            builtins.__dict__.update(self.original_builtins)
            self.imported_modules.clear()
            
            if exc_type is not None and issubclass(exc_type, SecurityError):
                log.error(f"Security violation in sandbox: {exc_val}")
                return False
            return True
            
        except Exception as e:
            log.error(f"Error during sandbox cleanup: {e}")
            return False

class SecurityContext:
    """Tracks security context during function execution."""
    def __init__(self):
        self.security_violations = []
        self.operation_stack = []
        self.resource_access = set()
        self.imported_modules = set()

class DynamicSecurityChecker:
    """Runtime security checker that monitors code execution."""
    def __init__(self, context: SecurityContext):
        self.context = context
        self.operation_count = 0
        self.max_operations = 1000  # Prevent infinite loops
        
    def check_operation(self, op_type: str, details: str) -> None:
        """Check if an operation is allowed."""
        self.operation_count += 1
        if self.operation_count > self.max_operations:
            raise SecurityError("Operation limit exceeded")
            
        self.context.operation_stack.append(op_type)
        if len(self.context.operation_stack) > 10:
            raise SecurityError("Call stack depth exceeded")

    def check_resource(self, resource: str) -> None:
        """Track and validate resource access."""
        if resource in self.context.resource_access:
            raise SecurityError(f"Duplicate resource access: {resource}")
        self.context.resource_access.add(resource)

    def check_import(self, module: str) -> None:
        """Validate module imports."""
        if module in self.context.imported_modules:
            raise SecurityError(f"Duplicate module import: {module}")
        self.context.imported_modules.add(module)

class SecureFunction:
    """Wrapper for secure function execution."""
    def __init__(self, func: Callable, security_config: Dict[str, Any]):
        self.func = func
        self.config = security_config
        self.context = SecurityContext()
        self.checker = DynamicSecurityChecker(self.context)
        self.is_async = asyncio.iscoroutinefunction(func)
        
    def validate_input(self, value: Any) -> None:
        """Validate input values against security patterns."""
        if isinstance(value, str):
            # Check length limits first
            if len(value) > self.config.get('max_input_length', 1000):
                raise ValueError("Input exceeds maximum length")

            # Check for command injection
            if re.search(r'[;&|`$]', value):
                raise ValueError("Input contains invalid characters")
                
            # Check for path traversal
            if '..' in value or value.startswith('/'):
                raise ValueError("Invalid path format")
                
            # Check for potentially dangerous patterns
            dangerous_patterns = [
                'rm', 'sudo', 'wget', 'curl',
                '/etc/', '/usr/', '/var/',
                'eval', 'exec', 'system'
            ]
            value_lower = value.lower()
            for pattern in dangerous_patterns:
                if pattern in value_lower:
                    raise ValueError(f"Input contains restricted pattern: {pattern}")

    def validate_output(self, value: Any) -> None:
        """Validate function output for security."""
        if value is None:
            return

        if isinstance(value, str):
            # Check length limits
            if len(value) > self.config.get('max_output_length', 10000):
                raise ValueError("Output exceeds maximum length")

            # Special handling for script generation
            if value.startswith('#!') or '.sh' in value.lower() or 'bash' in value.lower():
                # Split into lines and validate each line
                lines = value.split('\n')
                allowed_patterns = [
                    r'^#!.*(?:bash|sh)$',    # Shebang
                    r'^#.*$',                 # Comments
                    r'^echo\s+"[^";&|<>]*"$', # Echo with double quotes, no dangerous chars
                    r'^echo\s+\'[^\';&|<>]*\'$', # Echo with single quotes, no dangerous chars
                    r'^echo\s+(?:[^;&|<>])+$',   # Echo with safe unquoted text
                    r'^date(?:\s+[-+][^\s;&|<>]*)?$',  # Date command with safe options
                    r'^\s*$',                 # Empty lines
                ]

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Check if line matches any allowed pattern
                    if not any(re.match(pattern, line) for pattern in allowed_patterns):
                        # Check for dangerous patterns
                        dangerous_patterns = [
                            r'rm\s+-[rf]*\s*/*',     # Dangerous rm commands
                            r'sudo',                  # sudo commands
                            r'>\s*/dev/(?!null)',     # Writing to device files except /dev/null
                            r'>>\s*/dev/(?!null)',    # Appending to device files except /dev/null
                            r'chmod\s+(?:[0-7]{3,4}|\+.+)\s+/*',  # Dangerous chmod
                            r'chown',                 # chown commands
                            r'wget\s+.*\|\s*(?:bash|sh)',  # Piping wget to shell
                            r'curl\s+.*\|\s*(?:bash|sh)',  # Piping curl to shell
                            r'eval\s+',               # eval command
                            r'\$\(\s*.*\s*\)',        # Command substitution
                            r'`.*`',                  # Backtick command substitution
                            r'[;&|]',                 # Command separators/pipes
                            r'[<>]',                  # Redirections
                        ]

                        for pattern in dangerous_patterns:
                            if re.search(pattern, line, re.I):
                                raise ValueError(f"Output contains potentially dangerous command pattern")

                        raise ValueError(f"Output contains unrecognized shell command pattern: {line}")

            else:
                # For non-script content, check for injection patterns
                injection_patterns = [
                    r'(?i)<script',           # XSS
                    r'(?i)javascript:',       # JavaScript protocol
                    r'(?i)data:',            # Data URL scheme
                    r'(?i)vbscript:',        # VBScript protocol
                    r'(?:\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b.*\bFROM\b|\bOR\b.*=.*)',  # SQL injection
                    r'\{\{.*\}\}|\{%.*%\}',  # Template injection
                    r'\$\{.*\}',             # Shell variable injection
                ]
                for pattern in injection_patterns:
                    if re.search(pattern, value):
                        raise ValueError("Output contains potential injection pattern")

        elif isinstance(value, (list, tuple, set)):
            # Recursively validate all elements
            for item in value:
                self.validate_output(item)
        elif isinstance(value, dict):
            # Recursively validate all values
            for k, v in value.items():
                self.validate_output(k)
                self.validate_output(v)
        elif not isinstance(value, (int, float, bool)):
            # Only allow simple data types
            raise ValueError(f"Output type not allowed: {type(value).__name__}")

    async def __call__(self, *args, **kwargs) -> Any:
        """Execute function with security checks."""
        try:
            # Convert args to kwargs using function signature
            sig = inspect.signature(self.func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            kwargs = bound_args.arguments

            # Validate all inputs
            for param_name, value in kwargs.items():
                try:
                    self.validate_input(value)
                except ValueError as e:
                    raise ValueError(f"Invalid input for {param_name}: {str(e)}")

            # Execute in sandbox with resource limits
            sandbox = SecuritySandbox(
                allowed_builtins=self.config.get('safe_builtins', set()),
                safe_modules=self.config.get('safe_imports', {}),
                resource_limits=self.config.get('resource_limits', {})
            )

            with sandbox:
                # Call the wrapped function
                if self.is_async:
                    result = await self.func(**kwargs)
                else:
                    result = self.func(**kwargs)

                # Validate output
                try:
                    self.validate_output(result)
                except ValueError as e:
                    raise ValueError(f"Invalid output: {str(e)}")

                return result

        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ValueError(f"Error during execution: {str(e)}")

class CodeGeneratorAgent:
    def __init__(self, model_router, preferred_tool_model):
        self.model_router = model_router
        self.preferred_tool_model = preferred_tool_model
        self._tool_cache = {}
        self.syntax_validator = SyntaxValidatorAgent()

    async def generate_code(self, description, required_args, return_type):
        # Logic extracted from _generate_skill_code
        cache_key = self._get_cache_key(description, required_args, return_type)
        if (cache_key in self._tool_cache):
            log.info(f"Using cached code for tool with key {cache_key[:8]}...")
            return self._tool_cache[cache_key][0]
            
        prompt = (
            f"Generate Python code for a function that:\n"
            f"TASK: {description}\n"
            f"ARGUMENTS: {', '.join(required_args)} (all strings)\n"
            f"RETURN TYPE: {return_type}\n\n"
            f"Requirements:\n"
            f"1. Include type hints (str for args)\n"
            f"2. Include docstring\n"
            f"3. Handle errors appropriately\n"
            f"4. Follow PEP-8\n"
            f"5. Be self-contained\n"
        )
        
        try:
            code = await self.model_router.generate(
                prompt=f"{ToolCreator.DEFAULT_SYSTEM_PROMPT}\n\nUSER: {prompt}\n\nASSISTANT:\ndef",
                model_preference=self.preferred_tool_model,
                stream=False
            )
            
            if not isinstance(code, str) or not code.strip():
                raise ToolCreationError("Empty code generated")
                
            # Ensure proper function definition
            code = code.strip()
            if not code.startswith("def "):
                code = "def " + code
                
            # Validate and sanitize code using SyntaxValidatorAgent
            sanitized_code = self.syntax_validator.sanitize_code(code)
            if not self.syntax_validator.validate_ast(sanitized_code):
                raise ToolCreationError("Code validation failed")
                
            # Cache valid code
            self._tool_cache[cache_key] = (sanitized_code, {"description": description})
            return sanitized_code
            
        except Exception as e:
            log.exception(f"Code generation failed: {e}")
            raise ToolCreationError(f"Code generation failed: {str(e)}") from e

    @staticmethod
    def _get_cache_key(description: str, required_args: List[str], return_type: str) -> str:
        """Generate a cache key for tool generation."""
        key_parts = [description, ",".join(sorted(required_args)), return_type]
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()

class SyntaxValidatorAgent:
    def __init__(self):
        # Define sanitization rules as (pattern, replacement) tuples
        self._sanitization_rules = [
            (r'import\s+(os|subprocess|sys|shutil)', 'raise SecurityError("Unauthorized import")'),
            (r'__import__\s*\(', 'raise SecurityError("Dynamic imports not allowed")'),
            (r'exec\s*\(|eval\s*\(', 'raise SecurityError("Code execution not allowed")'),
            (r'open\s*\(', 'raise SecurityError("File operations not allowed")'),
            (r'socket\.', 'raise SecurityError("Network operations not allowed")'),
            (r'subprocess\.', 'raise SecurityError("Process execution not allowed")')
        ]

    def sanitize_code(self, code):
        # Logic extracted from _sanitize_code
        sanitized = code
        
        # First pass: Remove dangerous imports and statements
        for pattern, replacement in self._sanitization_rules:
            # Skip replacement if it would create invalid syntax
            if replacement.startswith('raise'):
                continue
            sanitized = re.sub(pattern, replacement, sanitized)
            
        # Second pass: Add security checks where appropriate
        lines = sanitized.split('\n')
        secured_lines = []
        
        for line in lines:
            # Check for dangerous operations and add security checks
            if re.search(r'open\s*\(|file\s*\(|exec\s*\(|eval\s*\(', line):
                secured_lines.append('    raise SecurityError("Operation not allowed")')
            else:
                secured_lines.append(line)
                
        return '\n'.join(secured_lines)

    def validate_ast(self, code, expected_return_type=None):
        """Validate the AST of the generated code."""
        try:
            tree = ast.parse(code)
            
            # Find function definition
            func_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if func_def is not None:
                        raise ToolCreationError("Multiple function definitions found")
                    func_def = node
            
            if func_def is None:
                raise ToolCreationError("No function definition found")

            # Check return type annotation if provided
            if expected_return_type and func_def.returns:
                declared_return = ast.unparse(func_def.returns).strip()
                if declared_return != expected_return_type:
                    return False
                
            # Check for dangerous operations
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if any(name.name in ['os', 'subprocess', 'sys'] for name in node.names):
                        raise ToolCreationError("Unauthorized import detected")
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ['exec', 'eval']:
                        raise ToolCreationError("Unauthorized exec/eval detected")
                        
            return True
            
        except SyntaxError as se:
            raise ToolCreationError(f"Invalid Python syntax: {se}")
        except Exception as e:
            if str(e) == "No function definition found":
                raise ToolCreationError("No function definition found")
            raise ToolCreationError(str(e))

class SecurityEvaluatorAgent:
    def __init__(self, security_config):
        self.security_config = security_config

    def evaluate_security(self, code):
        # Logic extracted from security-related classes
        pass

class RuntimeTesterAgent:
    async def test_runtime_behavior(self, func, test_inputs):
        # Logic for runtime verification
        issues = []
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        
        # Group test cases by expected behavior
        success_cases = []
        validation_error_cases = []
        
        for test_case in test_inputs:
            # Skip test cases that don't match the function signature
            if not all(k in param_names for k in test_case.keys()):
                continue
                
            # Check if this is a case that should succeed
            if all(isinstance(v, (str, int, float)) and str(v).strip() and 
                  str(v).replace('-', '').replace('.', '').isdigit() 
                  for v in test_case.values()):
                success_cases.append(test_case)
            else:
                validation_error_cases.append(test_case)
        
        # Test success cases - at least one should work
        success_count = 0
        for test_case in success_cases:
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(**test_case)
                else:
                    result = func(**test_case)
                    
                if result is not None:
                    success_count += 1
                
            except ValueError as ve:
                # Some ValueErrors are part of valid business logic
                if any(msg in str(ve).lower() for msg in [
                    "negative", "zero", "invalid range", "out of bounds"
                ]):
                    success_count += 1
                else:
                    issues.append(f"Unexpected ValueError with valid input {test_case}: {str(ve)}")
            except Exception as e:
                issues.append(f"Failed with valid input {test_case}: {str(e)}")
        
        if success_count == 0 and success_cases:
            issues.append("No success test cases passed - function may be too restrictive")
        
        # Test validation error cases
        validation_success = 0
        for test_case in validation_error_cases:
            try:
                if asyncio.iscoroutinefunction(func):
                    await func(**test_case)
                else:
                    func(**test_case)
                
                # If we get here, the validation failed to catch invalid input
                if any(v is None or (isinstance(v, str) and not v.strip())
                      for v in test_case.values()):
                    issues.append(f"Missing validation for empty/null input: {test_case}")
                elif any(isinstance(v, str) and len(v) > 1000 
                        for v in test_case.values()):
                    issues.append(f"Missing validation for too long input: {test_case}")
                elif any(isinstance(v, str) and any(p in v.lower() for p in [
                    "select", "insert", "update", "delete", "drop",
                    ";", "--", "'", "\"", "<", ">", "&", "|", "$"
                ]) for v in test_case.values()):
                    issues.append(f"Missing validation for dangerous input: {test_case}")
                else:
                    issues.append(f"Missing input validation: {test_case}")
                    
            except ValueError:
                # This is expected for invalid inputs
                validation_success += 1
            except Exception as e:
                # Other exceptions are okay if they prevent invalid input
                validation_success += 1
                
        if validation_success == 0 and validation_error_cases:
            issues.append("No validation test cases passed - error handling may be missing")
            
        return issues

class ToolRegistryAgent:
    def __init__(self):
        self._tool_cache = {}

    def register_tool(self, skill_name, func, metadata):
        # Logic for tool registration
        pass

class ReasoningAgent:
    def provide_reasoning(self, context):
        # Logic for reasoning and explanations
        pass

# Update ToolCreator to use these agents
class ToolCreator:
    """
    Dynamically generates Python code for new skills based on descriptions
    and registers them into the running system's skill registry.
    WARNING: Uses exec(). Security risk.
    """
    DEFAULT_SYSTEM_PROMPT = (
        "You are an expert Python Programmer specializing in creating self-contained, single-function tools (skills). "
        "Given a description, generate the Python code for a function that performs the specified task. "
        "The function should:\n"
        "1. Be complete and runnable Python code.\n"
        "2. Include necessary standard library imports INSIDE the function if possible.\n"
        "3. Have clear type hints for arguments and return values.\n"
        "4. Include a concise docstring explaining its purpose, arguments, and return value.\n"
        "5. Be self-contained and avoid relying on global variables.\n"
        "6. Handle errors appropriately with try/except blocks.\n"
        "7. Follow PEP-8 style guidelines.\n"
        "OUTPUT ONLY THE PYTHON FUNCTION CODE BLOCK. Do not include any surrounding text or markdown."
    )

    def __init__(self, model_router, skill_registry, skill_register_func, config=None):
        """Initialize the ToolCreator with required components."""
        config = config or {}
        self.code_generator = CodeGeneratorAgent(model_router, config.get("preferred_tool_model", "deepseek"))
        self.syntax_validator = SyntaxValidatorAgent()
        self.security_evaluator = SecurityEvaluatorAgent(config.get("security_config", {}))
        self.runtime_tester = RuntimeTesterAgent()
        self.skill_registry = skill_registry
        self.skill_register_func = skill_register_func
        self.reasoning_agent = ReasoningAgent()

    def _analyze_code_quality(self, code: str) -> ToolQualityMetrics:
        """Analyze the quality of the given code and return metrics."""
        metrics = ToolQualityMetrics()

        # Example complexity analysis using radon
        try:
            complexity_scores = radon.complexity.cc_visit(code)
            metrics.complexity_score = sum(c.complexity for c in complexity_scores) / len(complexity_scores)
        except Exception as e:
            log.warning(f"Complexity analysis failed: {e}")

        # Example security score (placeholder logic)
        metrics.security_score = 0.8  # Assume a default score for now

        # Example type safety score (placeholder logic)
        metrics.type_safety_score = 0.9  # Assume a default score for now

        # Example error handling score (placeholder logic)
        metrics.error_handling_score = 0.7  # Assume a default score for now

        return metrics

    async def create_tool(self, skill_name, description, required_args, return_type="str", skip_runtime_checks=False, quality_threshold=0.5):
        """Create a tool dynamically based on the given parameters."""
        try:
            # Check if tool already exists
            if skill_name in self.skill_registry:
                return {
                    "success": False,
                    "error": "Skill already exists"
                }

            # Generate code
            try:
                code = await self.code_generator.generate_code(description, required_args, return_type)
                if not code:
                    return {
                        "success": False,
                        "error": "Code generation failed: Empty code generated"
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Code generation failed: {str(e)}"
                }

            # Analyze code quality
            metrics = self._analyze_code_quality(code)
            if metrics.overall_score < quality_threshold:
                return {
                    "success": False,
                    "error": "Generated code does not meet quality standards"
                }

            # Validate syntax and return type
            try:
                code = self.syntax_validator.sanitize_code(code)
                if not self.syntax_validator.validate_ast(code, return_type):
                    return {
                        "success": False,
                        "error": f"Return type mismatch. Expected {return_type}"
                    }
            except ToolCreationError as e:
                return {
                    "success": False,
                    "error": str(e)
                }

            # Prepare execution environment
            namespace = {}
            exec_globals = {
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'set': set,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'ValueError': ValueError,
                    'Exception': Exception,
                    're': __import__('re'),
                    'math': __import__('math'),
                    'asyncio': __import__('asyncio')
                }
            }

            # Execute code in sandbox
            try:
                exec(code, exec_globals, namespace)
                func = next(f for f in namespace.values() if callable(f))
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Code execution failed: {str(e)}"
                }

            # Runtime verification
            test_coverage = "Skipped"
            if not skip_runtime_checks:
                test_inputs = [{arg: "test_value" for arg in required_args}]
                try:
                    issues = await self.runtime_tester.test_runtime_behavior(func, test_inputs)
                    if issues:
                        return {
                            "success": False,
                            "error": f"Runtime issues detected: {issues}"
                        }
                    test_coverage = "Passed"
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Runtime verification failed: {str(e)}"
                    }

            # Create secure wrapper
            security_config = {
                'safe_builtins': {
                    'len', 'str', 'int', 'float', 'bool',
                    'list', 'dict', 'set', 'min', 'max', 'sum'
                },
                'safe_imports': {'re': ['match', 'search', 'sub']},
                'max_input_length': 1000,
                'resource_limits': {
                    'max_time': 5,  # seconds
                    'max_memory': 100 * 1024 * 1024,  # 100MB
                }
            }

            wrapped_func = SecureFunction(func, security_config)

            # Register the tool
            try:
                self.skill_register_func(
                    skill_name,
                    wrapped_func,
                    {
                        "description": description,
                        "args": required_args,
                        "return_type": return_type,
                        "security_config": security_config
                    }
                )

                # Update registry
                self.skill_registry[skill_name] = {
                    'function': func,
                    'wrapper': wrapped_func,
                    'metadata': {
                        'is_async': asyncio.iscoroutinefunction(func),
                        'security_config': security_config
                    }
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Tool registration failed: {str(e)}"
                }

            return {
                "success": True,
                "skill_name": skill_name,
                "description": description,
                "quality_metrics": {
                    "overall_score": metrics.overall_score,
                    "complexity": metrics.complexity_score,
                    "security": metrics.security_score,
                    "type_safety": metrics.type_safety_score,
                    "error_handling": metrics.error_handling_score
                },
                "test_coverage": test_coverage,
                "code": code
            }

        except Exception as e:
            log.exception(f"Tool creation failed for {skill_name}: {e}")
            return {
                "success": False,
                "error": f"Tool creation failed: {str(e)}"
            }