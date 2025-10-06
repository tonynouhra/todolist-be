# Gemini API Rate Limiting & Quota Management Improvements

## Problem Statement

The application was encountering frequent Gemini API quota exceeded errors:

```
429 You exceeded your current quota, please check your plan and billing details.
Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests
limit: 2 requests/minute
Please retry in 32.984803332s
```

**Root Cause:** Using `gemini-2.5-pro` model with only 2 requests/minute on the free tier.

## Solution Overview

Implemented comprehensive rate limiting and retry logic with the following features:

1. **Exponential Backoff Retry Logic** - Automatic retries with increasing wait times
2. **Request Throttling** - Semaphore-based rate limiting to prevent overwhelming the API
3. **Intelligent Error Handling** - Parse retry delays from API responses
4. **Smart Model Selection** - Prioritize models with better rate limits

## Changes Made

### 1. Dependencies
**File:** `requirements.txt`

Added `tenacity==8.2.3` for robust retry logic with exponential backoff.

### 2. Configuration Updates
**File:** `app/core/config.py`

Added new configuration settings:

```python
# AI Rate Limiting & Retry
ai_max_retry_attempts: int = 3           # Max retry attempts
ai_retry_backoff_factor: float = 2.0     # Exponential backoff factor
ai_retry_min_wait: int = 1               # Min wait between retries (seconds)
ai_retry_max_wait: int = 60              # Max wait between retries (seconds)
ai_requests_per_minute: int = 15         # Rate limit (gemini-1.5-flash default)
```

### 3. AI Service Enhancements
**File:** `app/domains/ai/service.py`

#### A. Rate Limiting with Semaphore
```python
# Class-level semaphore for rate limiting (shared across instances)
_rate_limit_semaphore: asyncio.Semaphore | None = None

@classmethod
async def _get_semaphore(cls) -> asyncio.Semaphore:
    """Get or create the rate limit semaphore (thread-safe)."""
    if cls._rate_limit_semaphore is None:
        async with cls._semaphore_lock:
            if cls._rate_limit_semaphore is None:
                cls._rate_limit_semaphore = asyncio.Semaphore(
                    settings.ai_requests_per_minute
                )
    return cls._rate_limit_semaphore
```

#### B. Retry Logic with Tenacity
```python
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
    semaphore = await self._get_semaphore()
    async with semaphore:
        return await self._generate_content_async(prompt)
```

#### C. Retry Delay Parsing
```python
def _extract_retry_delay(self, error_message: str) -> int:
    """Extract retry delay from Gemini API error message.

    Pattern: "Please retry in 32.984803332s"
    """
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_message)
    if match:
        return int(float(match.group(1))) + 1  # Add 1 second buffer
    return settings.ai_retry_min_wait
```

#### D. Enhanced Error Detection
```python
# Check for specific error types (check quota first, as it often includes "429")
if "quota" in error_msg or "exceeded your current quota" in error_msg:
    raise AIQuotaExceededError(
        f"API quota exceeded. Please try again in {retry_delay} seconds",
        details={"retry_after": retry_delay, "error": full_error_msg}
    )
elif "429" in full_error_msg or ("rate" in error_msg and "limit" in error_msg):
    raise AIRateLimitError(
        f"Rate limit exceeded. Retry after {retry_delay} seconds",
        retry_after=retry_delay,
    )
```

#### E. Improved Model Selection
```python
def _get_available_model(self) -> str:
    """Get the first available model that supports generateContent.

    Priority order:
    1. gemini-1.5-flash (15 req/min free tier) - PREFERRED
    2. gemini-1.5-pro (15 req/min free tier)
    3. gemini-pro (60 req/min free tier, legacy)

    Avoids:
    - gemini-2.x models (only 2 req/min free tier - too restrictive)
    """
    # Filter out gemini-2.x models
    filtered_models = [m for m in model_names if "gemini-2." not in m]

    # Prioritize gemini-1.5-flash for best rate limits
    preferred_models = [
        "gemini-1.5-flash",        # 15 req/min - BEST for free tier
        "gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        ...
    ]
```

#### F. Enhanced Logging
Added emoji-based logging for better visibility:

```
✅ Google Gemini client initialized successfully
📊 Model: models/gemini-1.5-flash-001
⚡ Rate limit: 15 requests/minute
🔄 Max retries: 3 with exponential backoff
```

### 4. Environment Configuration
**File:** `.env.example`

Added configuration examples:

```bash
# AI Service
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_MAX_TOKENS=2048
AI_REQUEST_TIMEOUT=30

# AI Rate Limiting & Retry
AI_MAX_RETRY_ATTEMPTS=3
AI_RETRY_BACKOFF_FACTOR=2.0
AI_RETRY_MIN_WAIT=1
AI_RETRY_MAX_WAIT=60
AI_REQUESTS_PER_MINUTE=15
```

## How It Works

### Request Flow

1. **User Request** → AI endpoint
2. **Semaphore Acquisition** → Throttle to max requests/minute
3. **API Call with Retry** → Tenacity handles retries automatically
4. **Error Detection** → Parse error type and retry delay
5. **Exponential Backoff** → Wait with increasing delays (1s, 2s, 4s, ...)
6. **Success or Final Failure** → Return result or raise error

### Retry Example

If a quota exceeded error occurs:

1. **First attempt fails** → Extract retry delay (e.g., 33s)
2. **Wait 1 second** (min wait)
3. **Second attempt fails** → Wait 2 seconds (exponential backoff)
4. **Third attempt fails** → Wait 4 seconds
5. **Final attempt** → Either succeeds or raises AIQuotaExceededError

## Benefits

### 1. Better Rate Limit Handling
- ✅ Automatically retries when hitting rate limits
- ✅ Respects retry delays from API responses
- ✅ Uses exponential backoff to reduce API pressure

### 2. Improved Model Selection
- ✅ Prioritizes `gemini-1.5-flash` (15 req/min) over `gemini-2.5-pro` (2 req/min)
- ✅ Falls back gracefully if preferred model unavailable
- ✅ Clear logging shows which model is selected

### 3. Request Throttling
- ✅ Semaphore prevents exceeding rate limits
- ✅ Shared across all service instances
- ✅ Configurable via `AI_REQUESTS_PER_MINUTE`

### 4. User Experience
- ✅ Transparent retry logic - users don't see transient failures
- ✅ Better error messages with retry times
- ✅ Reduced 429 errors reaching frontend

## Testing

Comprehensive tests verify:
- ✅ Retry delay extraction from error messages
- ✅ Quota exceeded error detection
- ✅ Rate limit error detection
- ✅ Model selection logic
- ✅ Configuration loading

**Test Results:**
```
============================================================
All tests passed! ✅
============================================================

📊 Configuration Summary:
  - Model: models/gemini-1.5-flash-001
  - Max Retries: 3
  - Backoff Factor: 2.0
  - Min Wait: 1s
  - Max Wait: 60s
  - Requests/Min: 15
```

## Configuration Recommendations

### For Free Tier (Default)
```bash
GEMINI_MODEL=gemini-1.5-flash
AI_REQUESTS_PER_MINUTE=15
AI_MAX_RETRY_ATTEMPTS=3
```

### For Paid Tier
```bash
GEMINI_MODEL=gemini-1.5-pro
AI_REQUESTS_PER_MINUTE=60
AI_MAX_RETRY_ATTEMPTS=2  # Less retries needed
```

### For High Volume
```bash
GEMINI_MODEL=gemini-1.5-flash
AI_REQUESTS_PER_MINUTE=100
AI_RETRY_BACKOFF_FACTOR=1.5  # Faster retries
AI_RETRY_MAX_WAIT=30         # Lower max wait
```

## Monitoring

The service now logs:
- Model selection and rate limits on startup
- Retry attempts with delays
- Quota exceeded errors with full context
- Rate limit hits with retry delays

**Example Logs:**
```
INFO - ✅ Google Gemini client initialized successfully
INFO - 📊 Model: models/gemini-1.5-flash-001
INFO - ⚡ Rate limit: 15 requests/minute
WARNING - Rate limit hit. Retry after 5s
ERROR - Quota exceeded. Retry after 33s. Error: 429 You exceeded...
```

## Future Enhancements

Potential improvements:
1. **Redis-based rate limiting** - Track rate limits across multiple instances
2. **Quota usage dashboard** - Monitor API usage in real-time
3. **Dynamic rate adjustment** - Adjust based on current quota status
4. **Circuit breaker** - Temporarily disable AI when quota exhausted
5. **Priority queue** - Prioritize critical requests during rate limiting

## Troubleshooting

### Still hitting rate limits?
1. Check `AI_REQUESTS_PER_MINUTE` matches your model's limit
2. Verify model selection logs - ensure not using gemini-2.x
3. Consider reducing concurrent requests
4. Add Redis caching to reduce API calls

### Retries not working?
1. Check tenacity is installed: `pip list | grep tenacity`
2. Verify configuration in `.env`
3. Check logs for retry attempts
4. Ensure exceptions are properly raised

### Wrong model selected?
1. Check `GEMINI_MODEL` in `.env`
2. Review model selection logs on startup
3. Verify API key has access to preferred models
4. Check filtered models list in logs

## References

- [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Tenacity Documentation](https://tenacity.readthedocs.io/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
