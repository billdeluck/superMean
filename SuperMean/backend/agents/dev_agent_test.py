import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any

# Adjust path to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.agents.dev_agent import DevAgent
    from backend.models.model_router import ModelRouter
    from backend.memory.base_memory import BaseMemory
    from backend.skills import SkillError
    print("Imported DevAgent components successfully.")

    class TestDevAgent(unittest.TestCase):

        def setUp(self):
            """Create fresh mocks for each test."""
            self.setup_fresh_mocks()
            self.create_agent()
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def setup_fresh_mocks(self):
            """Setup fresh mock instances with default configurations."""
            self.mock_router_instance = MagicMock(spec=ModelRouter)
            self.mock_memory_instance = MagicMock(spec=BaseMemory)
            self.mock_execute_skill = AsyncMock()

            # Configure async methods
            self.mock_router_instance.generate = AsyncMock(return_value="Mock LLM Response")
            self.mock_memory_instance.store = AsyncMock(return_value=True)
            self.mock_execute_skill.return_value = "Generated Code"

        def create_agent(self):
            """Create a fresh agent instance with current mocks."""
            self.agent_id = "test_dev_agent_01"
            self.agent = DevAgent(
                agent_id=self.agent_id,
                model_router=self.mock_router_instance,
                agent_memory=self.mock_memory_instance,
                execute_skill_func=self.mock_execute_skill,
                config={
                    'preferred_coder_model': 'test_model',
                    'analysis_depth': 'deep'
                }
            )

        def run_async(self, coro):
            return asyncio.run(coro)

        def reset_mocks(self):
            """Reset mocks and recreate agent for clean test state."""
            self.setup_fresh_mocks()
            self.create_agent()

        def test_initialization_with_config(self):
            """Test agent initialization with configuration."""
            self.assertEqual(self.agent.preferred_coder_model, 'test_model')
            self.assertEqual(self.agent.config['analysis_depth'], 'deep')
            self.assertEqual(self.agent.config['code_style_guide']['python'], 'pep8')
            self.assertTrue(self.agent.config['auto_documentation'])
            print("Initialization with configuration test passed.")

        def test_run_code_writing_with_analysis(self):
            """Test code generation with dependency and quality analysis."""
            self.reset_mocks()
            
            task = "Write a Python function to process data"
            language = "python"
            code_response = "def process_data(): pass"
            dependency_result = "Required: pandas, numpy"
            quality_result = "Code quality: Good"
            
            self.mock_execute_skill.return_value = code_response
            self.mock_router_instance.generate.side_effect = [
                dependency_result,  # For dependency analysis
                quality_result     # For quality analysis
            ]

            result = self.run_async(self.agent.run(
                task_description=task,
                language=language,
                analysis_required=True,
                quality_check=True
            ))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['code'], code_response)
            self.assertEqual(result['language'], language)
            self.assertEqual(result['dependencies'], dependency_result)
            self.assertEqual(result['analysis'], quality_result)

            # Verify memory storage - using call_args_list properly
            store_calls = self.mock_memory_instance.store.call_args_list
            self.assertTrue(store_calls, "No store calls were made")
            
            for call in store_calls:
                if 'generated_code_python' in str(call):
                    self.assertEqual(call.kwargs['value'], code_response)
                    break
            else:
                self.fail("No store call found for generated code")
            print("Code writing with analysis test passed.")

        def test_run_debug_task(self):
            """Test debugging capabilities."""
            self.reset_mocks()
            
            task = "Debug this function"
            context = "def buggy(): return x + 1"
            debug_response = "Bug: x is undefined\nFix: Define x first"
            
            self.mock_router_instance.generate.return_value = debug_response

            result = self.run_async(self.agent.run(
                task_description=task,
                context=context
            ))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['debug_analysis'], debug_response)
            
            # Verify memory storage - using call_args_list properly
            store_calls = self.mock_memory_instance.store.call_args_list
            self.assertTrue(store_calls, "No store calls were made")
            
            for call in store_calls:
                if 'debug_session_' in str(call):
                    self.assertEqual(call.kwargs['metadata']['context'], context)
                    break
            else:
                self.fail("No store call found for debug session")
            print("Debug task test passed.")

        def test_run_code_analysis(self):
            """Test code analysis capabilities."""
            self.reset_mocks()
            
            task = "Analyze this code"
            context = "def quick_sort(arr): pass"
            analysis_response = "Analysis: Implementation incomplete"
            self.mock_router_instance.generate.return_value = analysis_response

            result = self.run_async(self.agent.run(
                task_description=task,
                context=context,
                language="python"
            ))

            self.assertEqual(result['status'], 'success')
            self.assertIn('analysis', result)
            self.assertEqual(result['analysis'], analysis_response)
            print("Code analysis test passed.")

        def test_implementation_planning(self):
            """Test implementation planning capabilities."""
            self.reset_mocks()
            
            task = "Implement a REST API"
            plan_response = "1. Define endpoints\n2. Implement handlers"
            self.mock_router_instance.generate.return_value = plan_response

            result = self.run_async(self.agent.run(
                task_description=task,
                plan_required=True
            ))

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['plan'], plan_response)
            
            # Verify memory storage - using call_args_list properly
            store_calls = self.mock_memory_instance.store.call_args_list
            self.assertTrue(store_calls, "No store calls were made")
            
            for call in store_calls:
                if 'implementation_plan_' in str(call):
                    self.assertEqual(call.kwargs['value'], plan_response)
                    break
            else:
                self.fail("No store call found for implementation plan")
            print("Implementation planning test passed.")

        def test_error_handling_missing_context(self):
            """Test error handling when context is missing for debug/analyze tasks."""
            self.reset_mocks()
            
            for task_type in ["Debug this", "Analyze this code"]:
                with self.assertRaises(ValueError) as cm:
                    self.run_async(self.agent.run(task_description=task_type))
                self.assertIn("context", str(cm.exception).lower())
            print("Error handling for missing context test passed.")

        def test_error_handling_skill_failure(self):
            """Test handling of skill execution failures."""
            self.reset_mocks()
            
            task = "Write code that fails"
            self.mock_execute_skill.side_effect = SkillError("Skill failed")

            with self.assertRaises(SkillError) as cm:
                self.run_async(self.agent.run(
                    task_description=task,
                    language="python"
                ))

            self.assertIn("Skill failed", str(cm.exception))
            print("Error handling for skill failure test passed.")

        def test_static_analysis(self):
            """Test static code analysis capabilities."""
            self.reset_mocks()
            
            code = "def process_data(data: list) -> None:\n    unused_var = 42\n    for i in data: pass"
            language = "python"
            analysis_result = "Found: unused variable 'unused_var', empty loop body"
            self.mock_router_instance.generate.return_value = analysis_result

            result = self.run_async(self.agent.analyze_static(code, language))
            
            self.assertEqual(result['static_analysis'], analysis_result)
            self.mock_router_instance.generate.assert_awaited_once()
            print("Static analysis test passed.")

        def test_runtime_analysis(self):
            """Test runtime debugging analysis."""
            self.reset_mocks()
            
            code = "def divide(a, b): return a/b"
            language = "python"
            error_context = "ZeroDivisionError: division by zero"
            debug_result = "Issue: No validation for zero divisor"
            self.mock_router_instance.generate.return_value = debug_result

            result = self.run_async(self.agent.debug_runtime(code, language, error_context))
            
            self.assertEqual(result['runtime_analysis'], debug_result)
            self.mock_router_instance.generate.assert_awaited_once()
            print("Runtime analysis test passed.")

        def test_refactoring_suggestions(self):
            """Test code refactoring analysis."""
            self.reset_mocks()
            
            code = "class User:\n    def get_name(self): return self.name\n    def get_age(self): return self.age"
            language = "python"
            suggestions = "Consider: Add @property decorators instead of get_ methods"
            self.mock_router_instance.generate.return_value = suggestions

            result = self.run_async(self.agent.suggest_refactoring(code, language))
            
            self.assertEqual(result['refactoring_suggestions'], suggestions)
            self.mock_router_instance.generate.assert_awaited_once()
            print("Refactoring suggestions test passed.")

        def test_performance_analysis(self):
            """Test performance analysis capabilities."""
            self.reset_mocks()
            
            code = "def find_duplicates(items):\n    return [x for x in items if items.count(x) > 1]"
            language = "python"
            analysis = "O(n²) complexity due to count() in list comprehension"
            self.mock_router_instance.generate.return_value = analysis

            result = self.run_async(self.agent.analyze_performance(code, language))
            
            self.assertEqual(result['performance_analysis'], analysis)
            self.mock_router_instance.generate.assert_awaited_once()
            print("Performance analysis test passed.")

        def test_security_analysis(self):
            """Test security analysis capabilities."""
            self.reset_mocks()
            
            code = "def process_input(user_data): eval(user_data)"
            language = "python"
            analysis = "Critical: Unsafe eval() with user input"
            self.mock_router_instance.generate.return_value = analysis

            result = self.run_async(self.agent.check_security(code, language))
            
            self.assertEqual(result['security_analysis'], analysis)
            self.mock_router_instance.generate.assert_awaited_once()
            print("Security analysis test passed.")

        def test_comprehensive_debug_workflow(self):
            """Test the complete debugging workflow with all analysis types."""
            self.reset_mocks()
            
            task = "Debug this problematic code"
            code = "def process_user_data(data):\n    return eval(data.strip())"
            language = "python"
            error_context = "NameError: name 'malicious_input' is not defined"

            # Setup mock responses for each analysis type
            self.mock_router_instance.generate.side_effect = [
                "Basic debug analysis result",           # Initial debug analysis
                "Static: Unsafe eval() usage",          # static analysis
                "Runtime: No input validation",         # runtime analysis
                "Performance: O(n) string operation",   # performance
                "Security: Critical eval() vulnerability",  # security
                "Refactor: Use json.loads() instead"   # refactoring
            ]

            result = self.run_async(self.agent.run(
                task_description=task,
                context=code,
                language=language,
                error_context=error_context,
                performance_check=True,
                security_check=True,
                refactor_check=True
            ))

            # Verify result structure
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['debug_analysis'], "Basic debug analysis result")
            self.assertEqual(result['static_analysis'], "Static: Unsafe eval() usage")
            self.assertEqual(result['runtime_analysis'], "Runtime: No input validation")
            self.assertEqual(result['performance_analysis'], "Performance: O(n) string operation")
            self.assertEqual(result['security_analysis'], "Security: Critical eval() vulnerability")
            self.assertEqual(result['refactoring_suggestions'], "Refactor: Use json.loads() instead")

            # Verify memory storage - using call_args_list properly
            store_calls = self.mock_memory_instance.store.call_args_list
            self.assertTrue(store_calls, "No store calls were made")
            
            debug_session_found = False
            for call in store_calls:
                if 'debug_session_' in str(call):
                    debug_session_found = True
                    metadata = call.kwargs['metadata']
                    self.assertEqual(metadata['language'], language)
                    self.assertEqual(metadata['context'], code)
                    self.assertEqual(metadata['error_context'], error_context)
                    self.assertTrue(metadata['performance_check'])
                    self.assertTrue(metadata['security_check'])
                    self.assertTrue(metadata['refactor_check'])
                    
                    # Verify all expected analysis types are present
                    expected_keys = {'status', 'debug_analysis', 'static_analysis', 'runtime_analysis',
                                    'performance_analysis', 'security_analysis', 'refactoring_suggestions'}
                    self.assertEqual(set(metadata['analysis_types']), expected_keys)
                    break
            
            self.assertTrue(debug_session_found, "No debug session store call found")
            print("Comprehensive debug workflow test passed.")

    # Run the tests
    if __name__ == '__main__':
        print("\nRunning Enhanced DevAgent tests...")
        unittest.main()

except ImportError as e:
    print(f"Failed to import components: {e}")
    print("Ensure agent/dev_agent.py and its dependencies exist.")
except Exception as e:
    print(f"An error occurred during test setup: {e}")