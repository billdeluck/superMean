# Directory: backend/agents/
# File: dev_agent.py
# Description: Agent specialized for software development tasks.

import asyncio
from typing import Any, Dict, Optional, Callable, Coroutine, List

from backend.agents.base_agent import BaseAgent, ExecuteSkillType
from backend.models.model_router import ModelRouter
from backend.memory.base_memory import BaseMemory
from backend.skills import SkillError
from backend.utils.logger import setup_logger

class DevAgent(BaseAgent):
    """
    An advanced agent specialized in software development tasks, with capabilities for
    code writing, debugging, refactoring, dependency analysis, and project management.
    """
    DEFAULT_SYSTEM_PROMPT = (
        "You are an expert Senior Software Engineer with deep knowledge across multiple programming "
        "languages, frameworks, and best practices. Your capabilities include:\n"
        "1. Writing clean, efficient, and well-documented code\n"
        "2. Debugging and troubleshooting complex issues\n"
        "3. Refactoring and optimizing existing code\n"
        "4. Managing dependencies and project structure\n"
        "5. Analyzing code quality and suggesting improvements\n"
        "6. Understanding and implementing design patterns\n"
        "Approach tasks systematically and consider security, performance, and maintainability."
    )

    def __init__(
        self,
        agent_id: str,
        model_router: ModelRouter,
        agent_memory: BaseMemory,
        execute_skill_func: ExecuteSkillType,
        config: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ):
        """Initialize the enhanced DevAgent with additional configuration options."""
        super().__init__(
            agent_id=agent_id,
            agent_name="DevAgent",
            model_router=model_router,
            agent_memory=agent_memory,
            execute_skill_func=execute_skill_func,
            config=config,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT
        )
        
        # Enhanced configuration with defaults
        self.config.setdefault('preferred_coder_model', "deepseek")
        self.config.setdefault('code_style_guide', {
            'python': 'pep8',
            'javascript': 'airbnb',
            'typescript': 'microsoft'
        })
        self.config.setdefault('analysis_depth', 'deep')  # quick, normal, deep
        self.config.setdefault('auto_documentation', True)
        self.config.setdefault('security_checks', True)
        
        self.preferred_coder_model = self.config['preferred_coder_model']
        self.log.info("Enhanced DevAgent initialized with advanced capabilities")

    async def analyze_dependencies(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code dependencies and suggest required packages."""
        try:
            analysis = await self._call_llm(
                prompt=f"Analyze the following {language} code and list required dependencies:\n{code}",
                model_preference=self.preferred_coder_model
            )
            return {'dependencies': analysis}
        except Exception as e:
            self.log.error(f"Dependency analysis failed: {e}")
            raise SkillError("Dependency analysis failed") from e

    async def plan_implementation(self, task_description: str) -> str:
        """Create a structured plan for implementing the requested feature."""
        try:
            plan_prompt = (
                "Create a detailed implementation plan for the following task:\n"
                f"{task_description}\n\n"
                "Include:\n"
                "1. Required files and changes\n"
                "2. Dependencies and prerequisites\n"
                "3. Implementation steps\n"
                "4. Testing strategy\n"
                "5. Potential challenges and mitigations"
            )
            plan = await self._call_llm(
                prompt=plan_prompt,
                model_preference=self.preferred_coder_model
            )
            await self._remember(f"implementation_plan_{task_description[:50]}", plan)
            return plan  # Return plan directly
        except Exception as e:
            self.log.error(f"Implementation planning failed: {e}")
            raise SkillError("Implementation planning failed") from e

    async def analyze_code_quality(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code quality and suggest improvements."""
        try:
            quality_prompt = (
                f"Analyze the following {language} code for:\n"
                "1. Code quality and maintainability\n"
                "2. Performance optimization opportunities\n"
                "3. Security vulnerabilities\n"
                "4. Best practices compliance\n"
                f"\n{code}"
            )
            analysis = await self._call_llm(
                prompt=quality_prompt,
                model_preference=self.preferred_coder_model
            )
            return {'analysis': analysis}
        except Exception as e:
            self.log.error(f"Code quality analysis failed: {e}")
            raise SkillError("Code quality analysis failed") from e

    async def analyze_static(self, code: str, language: str) -> Dict[str, Any]:
        """Perform static code analysis including type checking and complexity metrics."""
        try:
            analysis_prompt = (
                f"Perform comprehensive static analysis of the following {language} code:\n"
                "1. Type consistency and potential type errors\n"
                "2. Code complexity metrics\n"
                "3. Potential memory leaks\n"
                "4. Unused variables and imports\n"
                "5. Code structure and organization\n"
                f"\n{code}"
            )
            analysis = await self._call_llm(
                prompt=analysis_prompt,
                model_preference=self.preferred_coder_model
            )
            return {'static_analysis': analysis}
        except Exception as e:
            self.log.error(f"Static analysis failed: {e}")
            raise SkillError("Static analysis failed") from e

    async def debug_runtime(self, code: str, language: str, error_context: Optional[str] = None) -> Dict[str, Any]:
        """Analyze runtime behavior and debug issues with detailed steps."""
        try:
            debug_prompt = (
                f"Perform runtime analysis of the following {language} code:\n"
                f"{code}\n\n"
                f"Error context: {error_context if error_context else 'No specific error provided'}\n\n"
                "Provide:\n"
                "1. Runtime flow analysis\n"
                "2. Variable state tracking\n"
                "3. Edge case identification\n"
                "4. Step-by-step debugging guide\n"
                "5. Fix recommendations"
            )
            analysis = await self._call_llm(
                prompt=debug_prompt,
                model_preference=self.preferred_coder_model
            )
            return {'runtime_analysis': analysis}
        except Exception as e:
            self.log.error(f"Runtime analysis failed: {e}")
            raise SkillError("Runtime analysis failed") from e

    async def suggest_refactoring(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code for potential refactoring opportunities."""
        try:
            refactor_prompt = (
                f"Analyze the following {language} code for refactoring opportunities:\n"
                f"{code}\n\n"
                "Consider:\n"
                "1. Design patterns that could be applied\n"
                "2. Code duplication removal\n"
                "3. Function/method organization\n"
                "4. Class hierarchy improvements\n"
                "5. SOLID principles application"
            )
            suggestions = await self._call_llm(
                prompt=refactor_prompt,
                model_preference=self.preferred_coder_model
            )
            return {'refactoring_suggestions': suggestions}
        except Exception as e:
            self.log.error(f"Refactoring analysis failed: {e}")
            raise SkillError("Refactoring analysis failed") from e

    async def analyze_performance(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code for performance optimization opportunities."""
        try:
            performance_prompt = (
                f"Analyze the following {language} code for performance:\n"
                f"{code}\n\n"
                "Focus on:\n"
                "1. Time complexity analysis\n"
                "2. Memory usage patterns\n"
                "3. Resource utilization\n"
                "4. Bottleneck identification\n"
                "5. Optimization suggestions"
            )
            analysis = await self._call_llm(
                prompt=performance_prompt,
                model_preference=self.preferred_coder_model
            )
            return {'performance_analysis': analysis}
        except Exception as e:
            self.log.error(f"Performance analysis failed: {e}")
            raise SkillError("Performance analysis failed") from e

    async def check_security(self, code: str, language: str) -> Dict[str, Any]:
        """Perform security analysis of the code."""
        try:
            security_prompt = (
                f"Perform security analysis of the following {language} code:\n"
                f"{code}\n\n"
                "Check for:\n"
                "1. Common security vulnerabilities\n"
                "2. Input validation issues\n"
                "3. Authentication/authorization concerns\n"
                "4. Data exposure risks\n"
                "5. Secure coding practice violations"
            )
            analysis = await self._call_llm(
                prompt=security_prompt,
                model_preference=self.preferred_coder_model
            )
            return {'security_analysis': analysis}
        except Exception as e:
            self.log.error(f"Security analysis failed: {e}")
            raise SkillError("Security analysis failed") from e

    async def run(self, task_description: str, **kwargs) -> Any:
        """
        Execute a software development task with enhanced capabilities.
        
        Args:
            task_description: Description of the development task
            **kwargs:
                - language (str): Programming language
                - context (str): Existing code context
                - target_model (str): Model override
                - analysis_required (bool): Whether to perform code analysis
                - plan_required (bool): Whether to create implementation plan
                - quality_check (bool): Whether to perform quality analysis
                - security_check (bool): Whether to perform security analysis
                - llm_kwargs (dict): Additional LLM parameters

        Returns:
            Dict containing task results and any additional analysis
        """
        self.log.info(f"Received enhanced development task: {task_description[:100]}...")
        
        # Initialize result container
        result = {'status': 'pending'}

        try:
            # Optional implementation planning
            if kwargs.get('plan_required', False):
                result['plan'] = await self.plan_implementation(task_description)

            # Determine primary action
            task_lower = task_description.lower()
            if any(action in task_lower for action in ["write", "create", "generate", "refactor", "modify"]):
                action = "write_code"
            elif "debug" in task_lower or "fix" in task_lower:
                action = "debug_code"
            elif "analyze" in task_lower or "review" in task_lower:
                action = "analyze_code"
            else:
                action = "generic_dev_task"

            if action == "write_code":
                language = kwargs.get("language")
                if not language:
                    raise ValueError("The 'language' argument is required for writing code.")

                context = kwargs.get("context")
                target_model = kwargs.get("target_model", self.preferred_coder_model)
                
                self.log.info(f"Generating code in {language} using {target_model}")
                code = await self._use_skill(
                    "code.write",
                    description=task_description,
                    language=language,
                    context=context,
                    target_model=target_model,
                    **(kwargs.get('llm_kwargs', {}))
                )
                
                result['code'] = code
                result['language'] = language
                
                # Store the generated code
                await self._remember(
                    f"generated_code_{language}",
                    code,
                    {
                        "task": task_description,
                        "language": language,
                        "timestamp": kwargs.get('timestamp', ''),
                        "context": bool(context)
                    }
                )

                # Optional additional analysis
                if kwargs.get('analysis_required', False):
                    deps = await self.analyze_dependencies(code, language)
                    result['dependencies'] = deps['dependencies']  # Unwrap dependencies result directly
                
                if kwargs.get('quality_check', False):
                    quality = await self.analyze_code_quality(code, language)
                    result['analysis'] = quality['analysis']  # Unwrap quality analysis result

            elif action == "debug_code":
                if not kwargs.get("context"):
                    self.log.error("Context (code to debug) is required for debugging tasks")
                    raise ValueError("Context (code to debug) is required for debugging tasks")
                
                code = kwargs["context"]
                language = kwargs.get("language", "unknown")
                error_context = kwargs.get("error_context")
                
                # Basic debug analysis first
                debug_prompt = (
                    "Debug the following code and provide:\n"
                    "1. Issue identification\n"
                    "2. Root cause analysis\n"
                    "3. Suggested fixes\n"
                    "4. Preventive measures\n\n"
                    f"Code to debug:\n{code}"
                )
                
                result['debug_analysis'] = await self._call_llm(
                    prompt=debug_prompt,
                    model_preference=kwargs.get('target_model', self.preferred_coder_model)
                )
                
                # Perform all analyses in parallel
                analyses = await asyncio.gather(
                    self.analyze_static(code, language),
                    self.debug_runtime(code, language, error_context),
                    *([] if not kwargs.get('performance_check', False) else [self.analyze_performance(code, language)]),
                    *([] if not kwargs.get('security_check', False) else [self.check_security(code, language)]),
                    *([] if not kwargs.get('refactor_check', False) else [self.suggest_refactoring(code, language)])
                )

                # Unwrap analysis results directly
                result['static_analysis'] = analyses[0]['static_analysis']
                result['runtime_analysis'] = analyses[1]['runtime_analysis']

                # Add optional analyses based on flags
                current_index = 2
                if kwargs.get('performance_check', False):
                    result['performance_analysis'] = analyses[current_index]['performance_analysis']
                    current_index += 1
                if kwargs.get('security_check', False):
                    result['security_analysis'] = analyses[current_index]['security_analysis']
                    current_index += 1
                if kwargs.get('refactor_check', False):
                    result['refactoring_suggestions'] = analyses[current_index]['refactoring_suggestions']

                # Store debug session with comprehensive analysis
                metadata = {
                    "task": task_description,
                    "language": language,
                    "context": code,
                    "error_context": error_context,
                    "performance_check": kwargs.get('performance_check', False),
                    "security_check": kwargs.get('security_check', False),
                    "refactor_check": kwargs.get('refactor_check', False),
                    "analysis_types": list(result.keys())
                }
                
                await self._remember(
                    f"debug_session_{task_description[:50]}",
                    result,
                    metadata
                )

            elif action == "analyze_code":
                if not kwargs.get("context"):
                    raise ValueError("Context (code to analyze) is required for analysis tasks")
                
                code = kwargs['context']
                language = kwargs.get('language', 'unknown')
                
                # Perform code quality analysis
                analysis_result = await self.analyze_code_quality(code, language)
                result['analysis'] = analysis_result['analysis']  # Unwrap the analysis result directly
                
                # Store analysis results
                await self._remember(
                    f"code_analysis_{task_description[:50]}",
                    result,
                    {
                        "task": task_description,
                        "language": language,
                        "context": code,
                        "analysis_type": "quality"
                    }
                )

            else:
                # Generic development task
                response = await self._call_llm(
                    prompt=task_description,
                    model_preference=self.preferred_coder_model
                )
                result['response'] = response

            result['status'] = 'success'
            return result

        except ValueError as ve:
            # Let ValueError propagate directly for missing context
            self.log.error(f"Validation error during task execution: {ve}")
            raise

        except SkillError as e:
            self.log.error(f"Skill execution failed: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            raise

        except Exception as e:
            self.log.exception(f"Unexpected error during task execution: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            raise SkillError(f"DevAgent task execution failed: {e}") from e