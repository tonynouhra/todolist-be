"""AI service layer with Google Gemini integration."""

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.exceptions.ai import (
    AIConfigurationError,
    AIContentFilterError,
    AIInvalidRequestError,
    AIParsingError,
    AIQuotaExceededError,
    AIRateLimitError,
    AIServiceError,
    AIServiceUnavailableError,
    AITimeoutError,
)
from app.schemas.ai import (
    AIServiceStatus,
    FileAnalysisRequest,
    FileAnalysisResponse,
    GeneratedSubtask,
    GeneratedTodo,
    SubtaskGenerationRequest,
    SubtaskGenerationResponse,
    TaskOptimizationRequest,
    TaskOptimizationResponse,
    TodoSuggestionRequest,
    TodoSuggestionResponse,
)
from models.ai_interaction import AIInteraction
from models.file import File
from models.todo import Todo


logger = logging.getLogger(__name__)


class AIService:
    """Service class for AI operations using Google Gemini."""

    # Class-level semaphore for rate limiting (shared across instances)
    _rate_limit_semaphore: asyncio.Semaphore | None = None
    _semaphore_lock = asyncio.Lock()

    def __init__(self, db: AsyncSession):
        """Initialize AI service with database session.

        Args:
            db: Async database session for data operations.
        """
        self.db = db
        self.model = None
        self._initialize_client()
        self._last_request_time: float | None = None

    @classmethod
    async def _get_semaphore(cls) -> asyncio.Semaphore:
        """Get or create the rate limit semaphore (thread-safe)."""
        if cls._rate_limit_semaphore is None:
            async with cls._semaphore_lock:
                if cls._rate_limit_semaphore is None:
                    # Allow up to requests_per_minute concurrent requests
                    cls._rate_limit_semaphore = asyncio.Semaphore(settings.ai_requests_per_minute)
        return cls._rate_limit_semaphore

    def _initialize_client(self):
        """Initialize Google Gemini client."""
        if not settings.gemini_api_key:
            raise AIConfigurationError("Gemini API key not configured")

        try:
            genai.configure(api_key=settings.gemini_api_key)

            # Get the correct model name
            model_name = self._get_available_model()

            # Configure the model with safety settings
            self.model = genai.GenerativeModel(
                model_name=model_name,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: (HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: (HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: (HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: (HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                },
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=settings.gemini_max_tokens,
                    temperature=0.7,
                ),
            )
            logger.info("✅ Google Gemini client initialized successfully")
            logger.info(f"📊 Model: {model_name}")
            logger.info(f"⚡ Rate limit: {settings.ai_requests_per_minute} requests/minute")
            logger.info(f"🔄 Max retries: {settings.ai_max_retry_attempts} with exponential backoff")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            # Try to list available models for debugging
            try:
                available_models = list(genai.list_models())
                logger.info(f"Available models: {[model.name for model in available_models]}")
            except Exception:
                logger.warning("Could not list available models")
            raise AIConfigurationError(f"Failed to initialize AI service: {str(e)}") from e

    async def generate_subtasks(self, request: SubtaskGenerationRequest, user_id: UUID) -> SubtaskGenerationResponse:
        """Generate AI subtasks for an existing todo."""
        if not self.model:
            raise AIServiceUnavailableError("AI service not properly initialized")

        # Get the existing todo
        todo = await self._get_todo_by_id(request.todo_id, user_id)
        if not todo:
            raise AIInvalidRequestError("Todo not found or access denied")

        # Build the prompt using todo data
        prompt = self._build_subtask_generation_prompt_from_todo(todo, request.min_subtasks, request.max_subtasks)

        try:
            # Make the AI request with timeout and retry logic
            response = await asyncio.wait_for(
                self._generate_content_with_retry(prompt),
                timeout=settings.ai_request_timeout,
            )

            # Parse the response
            subtasks = self._parse_subtask_response(response)

            # Store the interaction
            await self._store_interaction(
                user_id=user_id,
                todo_id=todo.id,
                prompt=prompt,
                response=response,
                interaction_type="subtask_generation",
            )

            # Create subtask records in database
            for subtask_data in subtasks:
                subtask = Todo(
                    user_id=user_id,
                    project_id=todo.project_id,  # Inherit parent's project
                    parent_todo_id=todo.id,
                    title=subtask_data.title,
                    description=subtask_data.description,
                    status="todo",
                    priority=subtask_data.priority,
                    ai_generated=True,
                )

                self.db.add(subtask)

            # Commit all subtasks
            await self.db.commit()

            # Build response
            ai_response = SubtaskGenerationResponse(
                parent_task_title=todo.title,
                generated_subtasks=subtasks,
                total_subtasks=len(subtasks),
                generation_timestamp=datetime.now(UTC),
                ai_model=settings.gemini_model,
            )

            logger.info(f"Generated {len(subtasks)} subtasks for task: {todo.title}")
            return ai_response

        except TimeoutError:
            await self.db.rollback()
            raise AITimeoutError("AI request timed out") from None
        except json.JSONDecodeError as e:
            await self.db.rollback()
            raise AIParsingError(f"Failed to parse AI response: {str(e)}") from e
        except AIParsingError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            error_msg = str(e).lower()
            if "rate" in error_msg and "limit" in error_msg:
                raise AIRateLimitError("Rate limit exceeded") from e
            elif "quota" in error_msg:
                raise AIQuotaExceededError("API quota exceeded") from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise AIContentFilterError("Content blocked by safety filters") from e
            else:
                logger.error(f"AI service error: {str(e)}")
                raise AIServiceError(f"AI service error: {str(e)}") from e

    async def analyze_file(self, request: FileAnalysisRequest, user_id: UUID) -> FileAnalysisResponse:
        """Analyze a file using AI."""
        if not self.model:
            raise AIServiceUnavailableError("AI service not properly initialized")

        # Get file from database
        file = await self._get_file_by_id(request.file_id, user_id)
        if not file:
            raise AIInvalidRequestError("File not found or access denied")

        # Build analysis prompt based on file type and content
        prompt = self._build_file_analysis_prompt(file, request.analysis_type, request.context)

        try:
            response = await asyncio.wait_for(
                self._generate_content_with_retry(prompt),
                timeout=settings.ai_request_timeout,
            )

            # Parse analysis response
            analysis_data = self._parse_file_analysis_response(response)

            # Store interaction
            await self._store_interaction(
                user_id=user_id,
                prompt=prompt,
                response=response,
                interaction_type="file_analysis",
            )

            return FileAnalysisResponse(
                file_id=request.file_id,
                analysis_type=request.analysis_type,
                summary=analysis_data["summary"],
                key_points=analysis_data.get("key_points", []),
                suggested_tasks=analysis_data.get("suggested_tasks", []),
                confidence_score=analysis_data.get("confidence", 0.8),
                analysis_timestamp=datetime.now(UTC),
                ai_model=settings.gemini_model,
            )

        except TimeoutError:
            raise AITimeoutError("File analysis request timed out") from None
        except json.JSONDecodeError as e:
            raise AIParsingError(f"Failed to parse AI response: {str(e)}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg and "limit" in error_msg:
                raise AIRateLimitError("Rate limit exceeded") from e
            elif "quota" in error_msg:
                raise AIQuotaExceededError("API quota exceeded") from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise AIContentFilterError("Content blocked by safety filters") from e
            else:
                logger.error(f"AI service error: {str(e)}")
                raise AIServiceError(f"AI service error: {str(e)}") from e

    async def suggest_todos(self, request: TodoSuggestionRequest, user_id: UUID) -> TodoSuggestionResponse:
        """Generate AI todo suggestions based on user input."""
        if not self.model:
            raise AIServiceUnavailableError("AI service not properly initialized")

        # Build the prompt for todo suggestions
        prompt = self._build_todo_suggestion_prompt(request)

        try:
            response = await asyncio.wait_for(
                self._generate_content_with_retry(prompt),
                timeout=settings.ai_request_timeout,
            )

            # Parse the response
            todo_suggestions = self._parse_todo_suggestion_response(response)

            # Store the interaction
            await self._store_interaction(
                user_id=user_id,
                prompt=prompt,
                response=response,
                interaction_type="todo_suggestion",
            )

            ai_response = TodoSuggestionResponse(
                request_description=request.user_input,
                generated_todos=todo_suggestions,
                total_todos=len(todo_suggestions),
                generation_timestamp=datetime.now(UTC),
                ai_model=settings.gemini_model,
            )

            logger.info(f"Generated {len(todo_suggestions)} todo suggestions")
            return ai_response

        except TimeoutError:
            raise AITimeoutError("Todo suggestion request timed out") from None
        except json.JSONDecodeError as e:
            raise AIParsingError(f"Failed to parse AI response: {str(e)}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg and "limit" in error_msg:
                raise AIRateLimitError("Rate limit exceeded") from e
            elif "quota" in error_msg:
                raise AIQuotaExceededError("API quota exceeded") from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise AIContentFilterError("Content blocked by safety filters") from e
            else:
                logger.error(f"AI service error: {str(e)}")
                raise AIServiceError(f"AI service error: {str(e)}") from e

    async def optimize_task(self, request: TaskOptimizationRequest, user_id: UUID) -> TaskOptimizationResponse:
        """Optimize an existing task title and/or description using AI."""
        if not self.model:
            raise AIServiceUnavailableError("AI service not properly initialized")

        # If todo_id is provided, get the current todo data
        if request.todo_id:
            todo = await self._get_todo_by_id(request.todo_id, user_id)
            if not todo:
                raise AIInvalidRequestError("Todo not found or access denied")

            # Use todo data if not provided in request
            current_title = request.current_title or todo.title
            current_description = request.current_description or todo.description
        else:
            current_title = request.current_title
            current_description = request.current_description

        if not current_title and not current_description:
            raise AIInvalidRequestError("Either todo_id or current_title/description must be provided")

        # Build the optimization prompt
        prompt = self._build_task_optimization_prompt(
            current_title, current_description, request.optimization_type, request.context
        )

        try:
            response = await asyncio.wait_for(
                self._generate_content_with_retry(prompt),
                timeout=settings.ai_request_timeout,
            )

            # Parse the response
            optimization_data = self._parse_task_optimization_response(response)

            # Store the interaction
            await self._store_interaction(
                user_id=user_id,
                todo_id=request.todo_id,
                prompt=prompt,
                response=response,
                interaction_type="task_optimization",
            )

            ai_response = TaskOptimizationResponse(
                original_title=current_title,
                original_description=current_description,
                optimized_title=optimization_data.get("optimized_title"),
                optimized_description=optimization_data.get("optimized_description"),
                optimization_type=request.optimization_type,
                improvements=optimization_data.get("improvements", []),
                optimization_timestamp=datetime.now(UTC),
                ai_model=settings.gemini_model,
            )

            logger.info(f"Optimized task: {current_title[:50]}...")
            return ai_response

        except TimeoutError:
            raise AITimeoutError("Task optimization request timed out") from None
        except json.JSONDecodeError as e:
            raise AIParsingError(f"Failed to parse AI response: {str(e)}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg and "limit" in error_msg:
                raise AIRateLimitError("Rate limit exceeded") from e
            elif "quota" in error_msg:
                raise AIQuotaExceededError("API quota exceeded") from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise AIContentFilterError("Content blocked by safety filters") from e
            else:
                logger.error(f"AI service error: {str(e)}")
                raise AIServiceError(f"AI service error: {str(e)}") from e

    async def get_service_status(self) -> AIServiceStatus:
        """Get AI service status and usage information."""
        service_available = False
        actual_model_name = settings.gemini_model
        requests_today = 0

        try:
            # Get today's interaction count first (this should always work)
            today = datetime.now(UTC).date()
            query = select(AIInteraction).where(AIInteraction.created_at >= today)
            result = await self.db.execute(query)
            requests_today = len(result.scalars().all())

            # Check if AI service is configured
            if not settings.gemini_api_key:
                logger.warning("AI service not configured - no API key")
                return AIServiceStatus(
                    service_available=False,
                    model_name="not_configured",
                    last_request_timestamp=None,
                    requests_today=requests_today,
                )

            # Check if model is initialized
            if not self.model:
                logger.warning("AI model not initialized")
                return AIServiceStatus(
                    service_available=False,
                    model_name=actual_model_name,
                    last_request_timestamp=None,
                    requests_today=requests_today,
                )

            # Test service availability with a simple request
            test_prompt = "Respond with 'OK' if you can process this request."
            response = await asyncio.wait_for(self._generate_content_with_retry(test_prompt), timeout=5.0)

            service_available = "ok" in response.lower()

            return AIServiceStatus(
                service_available=service_available,
                model_name=actual_model_name,
                last_request_timestamp=datetime.now(UTC),
                requests_today=requests_today,
            )

        except TimeoutError:
            logger.error("Service status check timed out")
        except Exception as e:
            logger.error(f"Service status check failed: {str(e)}")

        # Return failed status
        return AIServiceStatus(
            service_available=False,
            model_name=actual_model_name,
            last_request_timestamp=None,
            requests_today=requests_today,
        )

    # Private helper methods

    def _build_subtask_generation_prompt_from_todo(self, todo: Todo, min_subtasks: int, max_subtasks: int) -> str:
        """Build prompt for subtask generation from todo data."""
        base_prompt = f"""
Given the following main task, generate a list of specific,
actionable subtasks that would help complete it efficiently.

**Main Task:** {todo.title}
"""

        if todo.description:
            base_prompt += f"**Description:** {todo.description}\n"

        if todo.priority:
            priority_text = ["very low", "low", "medium", "high", "very high"][todo.priority - 1]
            base_prompt += f"**Priority Level:** {priority_text}\n"

        if todo.due_date:
            base_prompt += f"**Due Date:** {todo.due_date.strftime('%Y-%m-%d')}\n"

        base_prompt += f"""
**Requirements:**
1. Generate between {min_subtasks} and {max_subtasks} subtasks
2. Each subtask should be specific and actionable
3. Order them logically for efficient completion
4. Include estimated time where relevant
5. Make sure subtasks are not too granular or too broad

**Response Format (JSON only):**
```json
{{
    "subtasks": [
        {{
            "title": "Subtask title (under 100 characters)",
            "description": "Brief description if needed (optional)",
            "priority": 3,
            "estimated_time": "30 minutes",
            "order": 1
        }}
    ]
}}
```

Generate practical, actionable subtasks that break down the main task effectively:
"""

        return base_prompt

    def _build_file_analysis_prompt(self, file: File, analysis_type: str, context: str | None) -> str:
        """Build prompt for file analysis."""
        prompt = f"""
Analyze the following file and provide insights based on the analysis type requested.

**File Information:**
- Name: {file.filename}
- Type: {file.content_type}
- Size: {file.file_size} bytes
- Analysis Type: {analysis_type}
"""

        if context:
            prompt += f"**Additional Context:** {context}\n"

        if analysis_type == "task_extraction":
            prompt += """
**Task:** Extract actionable tasks, todos, or action items from this file.

**Response Format (JSON):**
```json
{
    "summary": "Brief summary of the file content",
    "key_points": ["Important point 1", "Important point 2"],
    "suggested_tasks": ["Task 1", "Task 2", "Task 3"],
    "confidence": 0.85
}
```
"""
        elif analysis_type == "summary":
            prompt += """
**Task:** Provide a comprehensive summary of the file content.

**Response Format (JSON):**
```json
{
    "summary": "Detailed summary of the content",
    "key_points": ["Main point 1", "Main point 2", "Main point 3"],
    "suggested_tasks": [],
    "confidence": 0.90
}
```
"""
        else:  # general
            prompt += """
**Task:** Provide a general analysis of the file content
including key insights and potential action items.

**Response Format (JSON):**
```json
{
    "summary": "General analysis and overview",
    "key_points": ["Key insight 1", "Key insight 2"],
    "suggested_tasks": ["Suggested action 1", "Suggested action 2"],
    "confidence": 0.80
}
```
"""

        # Note: In a real implementation, you'd need to include the actual file content
        # This might require additional logic to extract text from different file types
        prompt += "\n**File Content:** [File content would be inserted here based on file type]"

        return prompt

    def _build_todo_suggestion_prompt(self, request: TodoSuggestionRequest) -> str:
        """Build prompt for AI todo suggestions."""
        prompt = f"""
Generate a list of actionable todo items based on the user's input.

**User Request:** {request.user_input}
"""

        if request.project_id:
            prompt += f"**Project Context:** This is for a specific project (ID: {request.project_id})\n"

        if request.existing_todos:
            existing_list = "\n".join([f"- {todo}" for todo in request.existing_todos[:10]])
            prompt += f"""
**Existing Todos for Context:**
{existing_list}
"""

        prompt += f"""
**Requirements:**
1. Generate between 1 and {request.max_todos} relevant todos
2. Make each todo specific and actionable
3. Consider the user's existing todos to avoid duplicates
4. Keep responses CONCISE - only include description/category/estimated_time if truly valuable
5. Assign appropriate priority levels (1=very low, 5=very high)

**Response Format (JSON only, BE CONCISE):**
```json
{{
    "todos": [
        {{
            "title": "Clear, actionable todo title",
            "priority": 3
        }}
    ]
}}
```

**Optional fields** (only include if valuable):
- "description": Brief 1-sentence description
- "estimated_time": Time estimate (e.g., "30 minutes")
- "category": Category name

Generate practical, concise todos. Keep it brief to avoid truncation:
"""

        return prompt

    def _build_task_optimization_prompt(
        self,
        title: str | None,
        description: str | None,
        optimization_type: str,
        context: str | None,
    ) -> str:
        """Build prompt for task optimization."""
        prompt = """
Optimize the following task to make it clearer, more actionable, and better organized.

**Current Task:**
"""

        if title:
            prompt += f"Title: {title}\n"
        if description:
            prompt += f"Description: {description}\n"

        prompt += f"""
**Optimization Type:** {optimization_type}
"""

        if context:
            prompt += f"**Additional Context:** {context}\n"

        if optimization_type == "title":
            prompt += """
**Task:** Improve only the task title to be more clear and actionable.

**Response Format (JSON):**
```json
{
    "optimized_title": "Improved title text",
    "improvements": ["List of specific improvements made"]
}
```
"""
        elif optimization_type == "description":
            prompt += """
**Task:** Improve only the task description to be more detailed and actionable.

**Response Format (JSON):**
```json
{
    "optimized_description": "Improved description with more detail and clarity",
    "improvements": ["List of specific improvements made"]
}
```
"""
        elif optimization_type == "both":
            prompt += """
**Task:** Improve both the title and description for maximum clarity and actionability.

**Response Format (JSON):**
```json
{
    "optimized_title": "Improved title text",
    "optimized_description": "Improved description with more detail",
    "improvements": ["List of specific improvements made"]
}
```
"""
        elif optimization_type == "clarity":
            prompt += """
**Task:** Focus on making the task clearer and easier to understand.

**Response Format (JSON):**
```json
{
    "optimized_title": "Clearer title if needed",
    "optimized_description": "Clearer description if needed",
    "improvements": ["List of clarity improvements made"]
}
```
"""
        else:  # detail
            prompt += """
**Task:** Add more helpful detail while keeping the task focused.

**Response Format (JSON):**
```json
{
    "optimized_title": "More detailed title if needed",
    "optimized_description": "More detailed description with specific steps",
    "improvements": ["List of detail improvements made"]
}
```
"""

        prompt += """
Make the task more actionable and well-defined:
"""

        return prompt

    def _extract_retry_delay(self, error_message: str) -> int:
        """Extract retry delay from Gemini API error message.

        Args:
            error_message: Error message from Gemini API

        Returns:
            Retry delay in seconds, or default value if not found
        """
        # Pattern: "Please retry in 32.984803332s"
        match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_message)
        if match:
            return int(float(match.group(1))) + 1  # Add 1 second buffer
        return settings.ai_retry_min_wait

    @retry(
        retry=retry_if_exception_type((AIRateLimitError, AIQuotaExceededError)),
        stop=stop_after_attempt(settings.ai_max_retry_attempts),
        wait=wait_exponential(
            multiplier=settings.ai_retry_backoff_factor,
            min=settings.ai_retry_min_wait,
            max=settings.ai_retry_max_wait,
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _generate_content_with_retry(self, prompt: str) -> str:
        """Generate content with exponential backoff retry logic."""
        # Acquire semaphore for rate limiting
        semaphore = await self._get_semaphore()
        async with semaphore:
            return await self._generate_content_async(prompt)

    async def _generate_content_async(self, prompt: str) -> str:
        """Generate content using Gemini API asynchronously."""
        try:
            # Run the synchronous Gemini API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))

            # Check if response exists
            if not response:
                raise AIServiceError("Empty response from AI service")

            # Check if candidates exist and are not empty
            if not hasattr(response, "candidates") or not response.candidates:
                logger.error("AI response has no candidates - content may be blocked")
                # Log prompt_feedback if available for debugging
                if hasattr(response, "prompt_feedback"):
                    logger.error(f"Prompt feedback: {response.prompt_feedback}")
                raise AIContentFilterError("Content was blocked by AI safety filters. Please rephrase your request.")

            # Get the first candidate
            candidate = response.candidates[0]

            # Check finish_reason for issues
            if hasattr(candidate, "finish_reason"):
                finish_reason = candidate.finish_reason
                logger.info(f"Response finish_reason: {finish_reason}")

                # Handle different finish reasons
                if finish_reason and finish_reason != 0:  # 0 = FINISH_REASON_UNSPECIFIED or STOP
                    # Map finish reasons (based on Gemini API docs)
                    # 1 = STOP (normal), 2 = MAX_TOKENS, 3 = SAFETY, 4 = RECITATION, 5 = OTHER
                    if finish_reason == 3:  # SAFETY
                        logger.error(f"Content blocked by safety filters. Finish reason: {finish_reason}")
                        raise AIContentFilterError(
                            "Content was blocked by AI safety filters. Please rephrase your request."
                        )
                    elif finish_reason == 2:  # MAX_TOKENS
                        logger.warning(f"Response truncated due to max tokens. Finish reason: {finish_reason}")
                        logger.warning(f"Current max_tokens setting: {settings.gemini_max_tokens}")
                        # Check if we have any content despite truncation
                        if not candidate.content or not candidate.content.parts:
                            logger.error("MAX_TOKENS hit but no partial content returned")
                            raise AIServiceError(
                                "Response was too long for the configured token limit. "
                                "Try reducing the number of items requested (e.g., max_todos or max_subtasks)."
                            )
                    elif finish_reason in [4, 5]:  # RECITATION or OTHER
                        logger.error(f"Response generation issue. Finish reason: {finish_reason}")
                        raise AIServiceError(
                            "AI could not generate a proper response. Please try again with different input."
                        )

            # Check if the candidate has content
            if not candidate.content:
                logger.error("AI response candidate has no content object")
                logger.error(f"Candidate details: {candidate}")
                raise AIServiceError("AI returned empty content")

            # Check if content has parts
            if not candidate.content.parts:
                logger.error("AI response candidate content has no parts")
                logger.error(f"Content details: {candidate.content}")
                raise AIServiceError("AI returned empty content")

            # Safely access the text
            try:
                text = response.text
                if not text or not text.strip():
                    logger.error("AI returned empty or whitespace-only text")
                    logger.error(f"Response parts: {candidate.content.parts}")
                    raise AIServiceError("AI returned empty text response")
                return text
            except IndexError as e:
                logger.error(f"Index error accessing response.text: {str(e)}")
                logger.error(f"Candidates length: {len(response.candidates)}")
                logger.error(f"Parts length: {len(candidate.content.parts) if candidate.content.parts else 0}")
                raise AIServiceError("AI response structure was invalid - candidates array issue") from e

        except AIContentFilterError:
            # Re-raise content filter errors as-is
            raise
        except AIServiceError:
            # Re-raise known AI service errors as-is
            raise
        except Exception as e:
            error_msg = str(e).lower()
            full_error_msg = str(e)

            # Parse retry delay from error message if available
            retry_delay = self._extract_retry_delay(full_error_msg)

            # Check for specific error types (check quota first, as it often includes "429")
            if "quota" in error_msg or "exceeded your current quota" in error_msg:
                logger.error(f"Quota exceeded. Retry after {retry_delay}s. Error: {full_error_msg}")
                raise AIQuotaExceededError(
                    f"API quota exceeded. Please try again in {retry_delay} seconds",
                    details={"retry_after": retry_delay, "error": full_error_msg},
                ) from e
            elif "429" in full_error_msg or ("rate" in error_msg and "limit" in error_msg):
                logger.warning(f"Rate limit hit. Retry after {retry_delay}s")
                raise AIRateLimitError(
                    f"Rate limit exceeded. Retry after {retry_delay} seconds",
                    retry_after=retry_delay,
                ) from e
            else:
                logger.error(f"Gemini API call failed: {full_error_msg}")
                raise AIServiceError(f"AI generation failed: {full_error_msg}") from e

    def _parse_subtask_response(self, response: str) -> list[GeneratedSubtask]:
        """Parse AI response into structured subtasks."""
        try:
            # Extract JSON from response (handle code blocks)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise AIParsingError("No JSON found in response")

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            subtasks = []
            for idx, subtask_data in enumerate(data.get("subtasks", []), 1):
                subtask = GeneratedSubtask(
                    title=subtask_data.get("title", f"Subtask {idx}"),
                    description=subtask_data.get("description"),
                    priority=subtask_data.get("priority", 3),
                    estimated_time=subtask_data.get("estimated_time"),
                    order=subtask_data.get("order", idx),
                )
                subtasks.append(subtask)

            return subtasks

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse subtask JSON: {str(e)}")
            raise AIParsingError(f"Invalid JSON response: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error parsing subtask response: {str(e)}")
            raise AIParsingError(f"Failed to parse response: {str(e)}") from e

    def _parse_file_analysis_response(self, response: str) -> dict[str, Any]:
        """Parse AI file analysis response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise AIParsingError("No JSON found in analysis response")

            json_str = response[json_start:json_end]
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis JSON: {str(e)}")
            raise AIParsingError(f"Invalid JSON in analysis response: {str(e)}") from e

    def _parse_todo_suggestion_response(self, response: str) -> list[GeneratedTodo]:
        """Parse AI response into structured todo suggestions."""
        try:
            # Extract JSON from response (handle code blocks)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise AIParsingError("No JSON found in todo suggestion response")

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            todos = []
            for idx, todo_data in enumerate(data.get("todos", []), 1):
                todo = GeneratedTodo(
                    title=todo_data.get("title", f"Generated Todo {idx}"),
                    description=todo_data.get("description"),
                    priority=todo_data.get("priority", 3),
                    estimated_time=todo_data.get("estimated_time"),
                    category=todo_data.get("category"),
                )
                todos.append(todo)

            return todos

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse todo suggestion JSON: {str(e)}")
            logger.error(f"Response excerpt: {response[:500]}...")

            # Try to parse partial/truncated JSON by attempting to fix common issues
            try:
                # Extract what we can from the response
                json_start = response.find("{")
                if json_start == -1:
                    raise AIParsingError("No JSON found in todo suggestion response")

                # Try to find the todos array even if JSON is incomplete
                todos_start = response.find('"todos"')
                if todos_start != -1:
                    logger.info("Attempting to extract partial todos from truncated response")
                    # This is a best-effort attempt - if it fails, we'll raise the original error
                    # We won't implement complex JSON repair here, just raise a helpful error

                raise AIParsingError(
                    f"Invalid JSON response (likely truncated due to token limit). "
                    f"Try reducing max_todos or making the request simpler. Error: {str(e)}"
                )
            except AIParsingError:
                raise

        except Exception as e:
            logger.error(f"Error parsing todo suggestion response: {str(e)}")
            raise AIParsingError(f"Failed to parse response: {str(e)}") from e

    def _parse_task_optimization_response(self, response: str) -> dict[str, Any]:
        """Parse AI task optimization response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise AIParsingError("No JSON found in optimization response")

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            # Ensure improvements is a list
            if "improvements" in data and not isinstance(data["improvements"], list):
                data["improvements"] = [str(data["improvements"])]

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse optimization JSON: {str(e)}")
            raise AIParsingError(f"Invalid JSON in optimization response: {str(e)}") from e

    async def _store_interaction(
        self,
        user_id: UUID,
        prompt: str,
        response: str,
        interaction_type: str,
        todo_id: UUID | None = None,
    ) -> None:
        """Store AI interaction in database."""
        try:
            interaction = AIInteraction(
                user_id=user_id,
                todo_id=todo_id,
                prompt=prompt,
                response=response,
                interaction_type=interaction_type,
            )

            self.db.add(interaction)
            await self.db.commit()

        except SQLAlchemyError as e:
            logger.error(f"Failed to store AI interaction: {str(e)}")
            await self.db.rollback()
            # Don't raise here - interaction storage failure shouldn't fail the main operation

    async def _get_file_by_id(self, file_id: UUID, user_id: UUID) -> File | None:
        """Get file by ID and verify user ownership."""
        query = select(File).where(File.id == file_id, File.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_todo_by_id(self, todo_id: UUID, user_id: UUID) -> Todo | None:
        """Get todo by ID and verify user ownership."""
        query = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _get_available_model(self) -> str:
        """Get the first available model that supports generateContent.

        Priority order:
        1. gemini-1.5-flash (15 req/min free tier) - PREFERRED
        2. gemini-1.5-pro (15 req/min free tier)
        3. gemini-pro (60 req/min free tier, legacy)

        Avoids:
        - gemini-2.x models (only 2 req/min free tier - too restrictive)
        """
        try:
            # First try the configured model
            available_models = list(genai.list_models())
            model_names = [
                model.name for model in available_models if "generateContent" in model.supported_generation_methods
            ]

            logger.info(f"🔍 Available Gemini models with generateContent: {model_names}")

            # IMPORTANT: Filter out gemini-2.x models to avoid strict rate limits
            # gemini-2.5-pro has only 2 req/min vs gemini-1.5-flash has 15 req/min
            filtered_models = [m for m in model_names if "gemini-2." not in m]
            logger.info(f"✅ Filtered models (excluding gemini-2.x for rate limits): {filtered_models}")

            # Try to find the configured model first (exact match or endswith)
            configured_model = settings.gemini_model

            # First try exact match in filtered list
            if configured_model in filtered_models:
                logger.info(f"✅ Using configured model (exact match): {configured_model}")
                return configured_model

            # Then try endsWith match in filtered list
            for model_name in filtered_models:
                if model_name.endswith(configured_model) or configured_model in model_name:
                    logger.info(f"✅ Using configured model (partial match): {model_name}")
                    return model_name

            # Fall back to preferred model names (prioritize gemini-1.5-flash for best rate limits)
            preferred_models = [
                "gemini-1.5-flash",  # 15 req/min - BEST for free tier
                "gemini-1.5-flash-latest",
                "models/gemini-1.5-flash",
                "gemini-1.5-pro",  # 15 req/min
                "gemini-1.5-pro-latest",
                "models/gemini-1.5-pro",
                "gemini-pro",  # 60 req/min (legacy)
                "models/gemini-pro",
            ]

            for preferred in preferred_models:
                for available in filtered_models:
                    if preferred in available or available.endswith(preferred.split("/")[-1]):
                        logger.warning(f"⚠️ Configured model not found. Using fallback: {available}")
                        return available

            # If no preferred model found, use the first available from filtered list
            if filtered_models:
                logger.warning(f"⚠️ No preferred models found! Using first available: {filtered_models[0]}")
                return filtered_models[0]

            # Last resort: use any available model (even gemini-2.x)
            if model_names:
                logger.error(f"❌ No gemini-1.x models found! Using gemini-2.x (strict rate limits): {model_names[0]}")
                logger.error("⚠️ WARNING: gemini-2.x models have only 2 req/min. Expect frequent rate limiting!")
                return model_names[0]

            raise AIConfigurationError("No models with generateContent support found")

        except Exception as e:
            logger.error(f"Failed to get available models: {str(e)}")
            # Last resort: return the configured model and let it fail with a clear error
            return settings.gemini_model
