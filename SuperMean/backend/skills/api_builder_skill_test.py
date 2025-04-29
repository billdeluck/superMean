# Test Snippet File: backend/skills/api_builder_skill_test.py
# Description: Verifies the api_builder_skill logic using a mocked ModelRouter.
# Command: python -m backend.skills.api_builder_skill_test

import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Adjust path if necessary to run from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # Import the skill function directly and SkillError
    from backend.skills.api_builder_skill import build_fastapi_endpoint
    from backend.skills import SkillError
    # We also need to mock the ModelRouter class
    from backend.models.model_router import ModelRouter
    print("Imported API builder skill components successfully.")

    # Example generated code structure (simplified)
    MOCK_GENERATED_API_CODE = """
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Schemas
class WidgetBase(BaseModel):
    name: str
    weight: Optional[float] = None

class WidgetCreate(WidgetBase):
    pass

class Widget(WidgetBase):
    id: int

# In-memory storage (example)
db_widgets: Dict[int, Widget] = {}
widget_id_counter: int = 0

router = APIRouter(prefix="/widgets", tags=["widgets"])

@router.post("/", response_model=Widget, status_code=201)
async def create_widget(widget: WidgetCreate):
    global widget_id_counter
    widget_id_counter += 1
    new_widget = Widget(id=widget_id_counter, **widget.model_dump())
    db_widgets[widget_id_counter] = new_widget
    return new_widget

# Add other endpoints GET, PUT, DELETE...
"""

    class TestApiBuilderSkill(unittest.TestCase):

        def setUp(self):
            # Create a mock ModelRouter instance
            self.mock_router = MagicMock(spec=ModelRouter)
            # IMPORTANT: Configure the generate method as AsyncMock
            self.mock_router.generate = AsyncMock()
            print(f"\n--- Starting test: {self._testMethodName} ---")

        def run_async(self, coro):
            return asyncio.run(coro)

        def test_build_simple_api(self):
            """Test generating a simple API structure."""
            description = "API to manage simple widgets."
            resource_name = "widget"
            fields = {"name": "str", "weight": "Optional[float]"}
            target_model = "deepseek" # Default

            # Configure mock return value
            self.mock_router.generate.return_value = MOCK_GENERATED_API_CODE

            # Call the skill
            result = self.run_async(build_fastapi_endpoint(
                description=description,
                resource_name=resource_name,
                fields=fields,
                model_router=self.mock_router
                # Use default target model
            ))

            # Assertions
            self.assertTrue("APIRouter" in result)
            self.assertTrue("WidgetBase" in result)
            self.assertTrue("WidgetCreate" in result)
            self.assertTrue("Widget(" in result) # Read schema
            self.assertTrue("db_widgets" in result)
            self.assertTrue("@router.post" in result)
            self.assertEqual(result, MOCK_GENERATED_API_CODE.strip())

            # Verify mock call
            self.mock_router.generate.assert_awaited_once()
            call_args = self.mock_router.generate.await_args
            prompt = call_args.kwargs['prompt']
            self.assertIn(description, prompt)
            self.assertIn(resource_name, prompt)
            self.assertIn("name: str", prompt)
            self.assertIn("weight: Optional[float]", prompt)
            self.assertEqual(call_args.kwargs['model_preference'], target_model)
            print("Simple API generation test passed.")

        def test_build_api_with_target_model(self):
            """Test specifying a different target model."""
            description = "User API"
            resource_name = "user"
            fields = {"username": "str", "email": "str", "is_active": "bool = True"}
            target_model = "aimlapi:gpt-4o"

            self.mock_router.generate.return_value = "## MOCK USER API CODE ##"

            result = self.run_async(build_fastapi_endpoint(
                description=description,
                resource_name=resource_name,
                fields=fields,
                model_router=self.mock_router,
                target_model=target_model # Override default
            ))

            self.assertEqual(result, "## MOCK USER API CODE ##")
            self.mock_router.generate.assert_awaited_once()
            call_args = self.mock_router.generate.await_args
            self.assertEqual(call_args.kwargs['model_preference'], target_model)
            print("API generation with specific target model passed.")

        def test_generation_failure(self):
            """Test handling of errors from the model router."""
            description = "Failing API"
            resource_name = "error"
            fields = {"code": "int"}

            # Configure mock to raise an error
            self.mock_router.generate.side_effect = SkillError("LLM API generation failed")

            with self.assertRaises(SkillError) as cm:
                 self.run_async(build_fastapi_endpoint(
                    description=description,
                    resource_name=resource_name,
                    fields=fields,
                    model_router=self.mock_router
                 ))

            self.assertIn("API Builder skill failed", str(cm.exception))
            self.assertIn("LLM API generation failed", str(cm.exception)) # Check original error context
            print(f"Caught expected SkillError on API generation failure: {cm.exception}")


    # Run the tests
    print("\nRunning API Builder Skill tests...")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestApiBuilderSkill))
    runner = unittest.TextTestRunner()
    runner.run(suite)


except ImportError as e:
    print(f"Failed to import components: {e}")
    print("Ensure skill file, registry (__init__.py), ModelRouter, and utils exist.")
except Exception as e:
    print(f"An error occurred during test setup: {e}")