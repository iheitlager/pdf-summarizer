# ADR-0010: Use Flask-Limiter for Rate Limiting

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: Prevent abuse and manage API costs

## Context

The PDF Summarizer makes expensive Claude API calls for each uploaded PDF. Without rate limiting, the application is vulnerable to:

- **API cost abuse**: Malicious users uploading many PDFs to exhaust API credits
- **Service degradation**: Too many simultaneous requests overwhelming the server
- **Resource exhaustion**: Disk space filled with uploaded files
- **API quota limits**: Exceeding Anthropic's rate limits and getting throttled

Key requirements:
- **Prevent abuse**: Limit uploads per user/IP address
- **Simple implementation**: Minimal code and configuration
- **Configurable limits**: Easy to adjust rates without code changes
- **Good UX**: Clear error messages when limits are exceeded
- **Development friendly**: Easy to disable for testing

### Expected Usage Patterns
- Normal users: 1-10 uploads/day
- Burst usage: 2-5 uploads in quick succession
- API costs: $0.03-$0.15 per upload
- Server capacity: 10-50 concurrent requests

## Decision

Use **Flask-Limiter** extension to implement rate limiting on upload endpoints.

Flask-Limiter provides:
- **Decorator-based limits**: Simple `@limiter.limit()` on routes
- **Multiple strategies**: Per-IP, per-user, per-session
- **Storage backends**: In-memory, Redis, Memcached
- **Clear error messages**: Automatic 429 responses with retry-after headers
- **Flexible configuration**: String-based rate expressions ("10 per hour")
- **Testing support**: Easy to disable in test environments

### Rate Limits
- **Upload endpoint**: 10 uploads per hour per IP
- **General requests**: 200 requests per day per IP
- **Storage**: In-memory (suitable for single-server deployment)

### Implementation
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day"],
    storage_uri="memory://"
)

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per hour")
def upload():
    # Handle upload
    pass
```

## Alternatives Considered

### Alternative 1: Custom Rate Limiting Middleware
- **Description**: Build custom rate limiter using session tracking
- **Pros**:
  - Full control over implementation
  - No external dependencies
  - Custom logic possible (e.g., tiered limits)
  - Can track in database
- **Cons**:
  - Significant development effort
  - Need to implement storage, cleanup, error handling
  - Reinventing the wheel
  - Likely to have bugs
  - Maintenance burden
  - No community support
- **Rejected because**: Flask-Limiter is battle-tested and feature-complete. Building custom rate limiter is time-consuming and error-prone without benefits.

### Alternative 2: NGINX Rate Limiting
- **Description**: Use NGINX `limit_req` module at reverse proxy level
- **Pros**:
  - Very fast (C implementation)
  - Protects before request reaches Flask
  - Works across multiple app instances
  - Battle-tested in production
  - Protects against DDoS
- **Cons**:
  - Requires NGINX deployment
  - Configuration outside application code
  - Less flexible per-route limits
  - Harder to customize error responses
  - Not suitable for development server
  - Must configure separately from app
- **Rejected because**: Requires NGINX infrastructure. Development server (Flask) doesn't have NGINX. Application-level rate limiting is more portable and easier to configure.

### Alternative 3: CloudFlare/AWS WAF Rate Limiting
- **Description**: Use cloud provider rate limiting (CloudFlare, AWS WAF)
- **Pros**:
  - Protects before traffic reaches server
  - DDoS protection included
  - Global rate limiting across regions
  - Professional monitoring tools
  - No application code changes
- **Cons**:
  - Requires cloud provider account
  - Additional monthly costs ($20+/month)
  - Less granular control (per-route limits)
  - Overkill for simple app
  - Not suitable for self-hosted deployments
  - Configuration outside codebase
- **Rejected because**: Adds external dependency and cost. PDF Summarizer targets self-hosted deployments. Application-level rate limiting is free and portable.

### Alternative 4: API Key-Based Rate Limiting
- **Description**: Require API keys for uploads, limit per key
- **Pros**:
  - More accurate user tracking
  - Can assign different limits per user
  - Better for paid tiers
  - Prevents IP-based circumvention
- **Cons**:
  - Requires user registration system
  - Need API key generation/management
  - Poor UX (users must sign up)
  - Adds authentication complexity
  - Not suitable for simple upload tool
- **Rejected because**: PDF Summarizer intentionally has no authentication (see ADR-0007). API keys add complexity and hurt user experience. IP-based limiting is sufficient.

### Alternative 5: No Rate Limiting
- **Description**: Trust users and rely on Anthropic's rate limits
- **Pros**:
  - Simplest implementation
  - No restrictions on legitimate users
  - No additional code
- **Cons**:
  - Vulnerable to abuse (cost and resource)
  - Could exhaust API credits quickly
  - No protection against malicious uploads
  - Disk fills up with uploads
  - Poor cost control
- **Rejected because**: Claude API calls are expensive. Without rate limiting, a malicious user could upload hundreds of PDFs and incur hundreds of dollars in costs. Unacceptable risk.

## Consequences

### Positive Consequences
- **Cost protection**: Limits prevent runaway API costs
- **Simple integration**: Decorator-based, minimal code
- **Clear errors**: Automatic 429 responses with retry-after headers
- **Configurable**: Easy to adjust limits via environment variables
- **Good UX**: Legitimate users rarely hit limits (10/hour generous)
- **Testing friendly**: Can disable with `RATE_LIMIT_ENABLED=false`
- **No infrastructure**: In-memory storage works for single-server

### Negative Consequences
- **Shared IP limitations**: Multiple users behind same NAT may share limits
- **Proxy issues**: Users behind proxies may be identified incorrectly
- **In-memory limits**: Restarting app resets counters (users get fresh limits)
- **Single-server only**: In-memory storage doesn't work across multiple servers
- **Bypass possible**: Users can change IP to reset limits (acceptable risk)

### Neutral Consequences
- **429 status codes**: Clients must handle rate limit errors
- **No persistent tracking**: Limits reset on app restart
- **IP-based**: Proxies/VPNs may affect tracking

## Implementation Notes

### Flask-Limiter Setup
```python
# src/pdf_summarizer/main.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.RATE_LIMIT_DEFAULT],  # "200 per day"
    storage_uri=config.RATE_LIMIT_STORAGE_URI,   # "memory://"
    enabled=config.RATE_LIMIT_ENABLED             # true
)
```

### Route-Specific Limits
```python
@app.route('/upload', methods=['POST'])
@limiter.limit(config.RATE_LIMIT_UPLOAD)  # "10 per hour"
def upload():
    # Upload handling
    pass

@app.route('/results/<int:upload_id>')
@limiter.exempt  # No rate limit on viewing results
def results(upload_id):
    # Display results
    pass
```

### Error Handling
```python
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors."""
    return render_template(
        'errors/429.html',
        message="Too many uploads. Please try again later.",
        retry_after=e.description
    ), 429
```

### Configuration
```python
# src/pdf_summarizer/config.py
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")
RATE_LIMIT_UPLOAD = os.getenv("RATE_LIMIT_UPLOAD", "10 per hour")
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "200 per day")
```

### Code Locations
- Limiter setup: [src/pdf_summarizer/main.py:73-78](../../src/pdf_summarizer/main.py#L73-L78)
- Upload rate limit: [src/pdf_summarizer/main.py:296](../../src/pdf_summarizer/main.py#L296)
- Error handler: [src/pdf_summarizer/main.py:411-418](../../src/pdf_summarizer/main.py#L411-L418)
- Configuration: [src/pdf_summarizer/config.py:36-40](../../src/pdf_summarizer/config.py#L36-L40)

### Dependencies
```toml
# pyproject.toml
dependencies = [
    "flask-limiter>=3.5.0,<4.0.0",
]
```

## Rate Limit Strategies

### Rate Limit Expressions
```python
# Time-based
"10 per hour"      # 10 requests per hour
"100 per day"      # 100 requests per 24 hours
"5 per minute"     # 5 requests per minute

# Multiple limits (most restrictive applies)
"5 per minute; 50 per hour; 200 per day"

# Burst limits
"10/minute; 100/hour"  # Short burst allowed, but hourly cap
```

### Key Functions
```python
# By IP address (default)
key_func=get_remote_address

# By session ID
def get_session_id():
    return session.get('user_id', get_remote_address())
key_func=get_session_id

# Combined IP + session
def get_user_key():
    session_id = session.get('user_id', 'anon')
    ip = get_remote_address()
    return f"{session_id}:{ip}"
key_func=get_user_key
```

### Conditional Limits
```python
@limiter.limit("10 per hour", exempt_when=lambda: current_user.is_admin)
def upload():
    pass
```

## Storage Backends

### In-Memory (Default)
```python
storage_uri = "memory://"
# Pros: No dependencies, fast
# Cons: Resets on restart, single-server only
```

### Redis (Production)
```python
storage_uri = "redis://localhost:6379"
# Pros: Persistent, multi-server support
# Cons: Requires Redis infrastructure
```

### Memcached
```python
storage_uri = "memcached://localhost:11211"
# Pros: Distributed caching
# Cons: Requires Memcached
```

## Testing

### Disable in Tests
```python
# tests/conftest.py
@pytest.fixture
def app():
    app.config['RATE_LIMIT_ENABLED'] = False
    yield app
```

### Test Rate Limiting
```python
def test_upload_rate_limit(client):
    """Test upload rate limit enforcement."""
    # Make 10 uploads (at limit)
    for i in range(10):
        response = client.post('/upload', data={'pdf': pdf_file})
        assert response.status_code == 200

    # 11th upload should be rate limited
    response = client.post('/upload', data={'pdf': pdf_file})
    assert response.status_code == 429
    assert 'Retry-After' in response.headers
```

## Monitoring

### Rate Limit Headers
```python
# Response headers include:
X-RateLimit-Limit: 10          # Limit per period
X-RateLimit-Remaining: 7       # Remaining requests
X-RateLimit-Reset: 1699564800  # Timestamp when limit resets
Retry-After: 3600              # Seconds until retry allowed
```

### Logging
```python
from flask_limiter import RateLimitExceeded

@limiter.request_filter
def log_rate_limits():
    logger.debug(f"Rate limit check: {request.endpoint} from {get_remote_address()}")

@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    logger.warning(f"Rate limit exceeded: {get_remote_address()} on {request.endpoint}")
    return ..., 429
```

## Cost Analysis

### Without Rate Limiting
- Malicious user uploads 100 PDFs/hour
- Cost: 100 × $0.05 = **$5/hour** = **$120/day**
- Unacceptable cost exposure

### With Rate Limiting (10/hour)
- Maximum uploads: 10/hour per IP
- Maximum cost per IP: 10 × $0.05 = **$0.50/hour**
- With 100 users: **$50/hour** (still high, but predictable)

### Recommended Limits
- **Development**: No limits (disable)
- **Staging**: Relaxed limits (50/hour) for testing
- **Production**: Strict limits (10/hour) for cost control

## References

- [Flask-Limiter Documentation](https://flask-limiter.readthedocs.io/)
- [Rate Limiting Strategies](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
- [HTTP 429 Too Many Requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429)

## Related ADRs

- Related to: ADR-0001 (Use Flask as Web Framework)
- Related to: ADR-0004 (Use Anthropic Claude API) - Cost protection
- Related to: ADR-0007 (Session-Based User Tracking) - Alternative to key_func
