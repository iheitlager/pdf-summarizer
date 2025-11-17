# ADR-0004: Use Anthropic Claude API for Summarization

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: AI-powered PDF summarization engine selection

## Context

The PDF Summarizer requires an AI model to generate high-quality summaries of PDF documents. The model must understand long-form text, maintain context across multiple pages, and produce concise, accurate summaries.

Key requirements:
- **Long context window**: Handle PDFs with 10+ pages (up to 50K+ tokens)
- **High-quality output**: Accurate, coherent, well-structured summaries
- **Reasonable cost**: Balance quality with API pricing
- **Reliable API**: Production-grade uptime and performance
- **Developer experience**: Good SDK, documentation, and error handling
- **Content safety**: Handle sensitive documents appropriately

### PDF Characteristics
- Average document size: 5-20 pages (~10K-40K tokens)
- Content types: Technical reports, research papers, business documents
- Text extraction: Using pypdf library (unformatted text)

## Decision

Use **Anthropic's Claude API** (Claude 3.5 Sonnet model) for PDF summarization.

Claude provides:
- **200K token context window**: Handles PDFs up to ~150 pages
- **Superior summarization**: Excellent at distilling key points
- **Balanced pricing**: $3 per million input tokens, $15 per million output tokens
- **Production-ready API**: 99.9% uptime SLA
- **Python SDK**: Official `anthropic` library with async support
- **Streaming support**: Can stream responses for better UX
- **Content policy**: Clear guidelines for acceptable use

### Implementation
```python
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": f"Summarize this PDF content:\n\n{text}"
    }]
)
summary = response.content[0].text
```

## Alternatives Considered

### Alternative 1: OpenAI GPT-4
- **Description**: OpenAI's GPT-4 Turbo with 128K context window
- **Pros**:
  - Very high quality summaries
  - Large ecosystem and community
  - Well-documented API
  - Streaming support
  - Function calling capabilities
- **Cons**:
  - More expensive: $10/$30 per million tokens (3x Claude cost)
  - Smaller context window: 128K vs 200K tokens
  - Content policy more restrictive
  - Rate limits more aggressive
  - No specific summarization optimization
- **Rejected because**: Higher cost with smaller context window. Claude 3.5 Sonnet provides comparable quality at better price point for summarization tasks.

### Alternative 2: Google Gemini Pro
- **Description**: Google's Gemini 1.5 Pro with 1M token context window
- **Pros**:
  - Massive context window (1M tokens)
  - Native PDF processing (no extraction needed)
  - Competitive pricing
  - Multimodal capabilities
  - Good summarization quality
- **Cons**:
  - Less mature API (frequent changes)
  - Python SDK less polished
  - Fewer examples and community resources
  - Rate limits unpredictable
  - API stability concerns in production
- **Rejected because**: While the massive context window is impressive, API maturity and developer experience are not yet production-grade. Claude provides better stability.

### Alternative 3: Cohere Summarize API
- **Description**: Cohere's specialized summarization endpoint
- **Pros**:
  - Purpose-built for summarization
  - Simple API (one endpoint)
  - Competitive pricing
  - Good for short documents
  - Extractive + abstractive modes
- **Cons**:
  - Limited context window (5K tokens)
  - Not suitable for long PDFs
  - Less flexible than general LLMs
  - Smaller ecosystem
  - Cannot customize prompts as easily
- **Rejected because**: 5K token limit is insufficient for multi-page PDFs. Our documents often exceed 10K tokens, requiring a larger context window.

### Alternative 4: Open Source Models (Llama, Mistral)
- **Description**: Self-hosted open source LLMs (Llama 3, Mistral)
- **Pros**:
  - No per-token costs (only infrastructure)
  - Full control over deployment
  - Data privacy (on-premise)
  - No rate limits
  - Customizable fine-tuning
- **Cons**:
  - Requires GPU infrastructure ($500+/month)
  - DevOps complexity (deployment, monitoring, scaling)
  - Lower quality than Claude/GPT-4
  - Context windows typically smaller (32K-128K)
  - No managed API (build everything)
  - Ongoing maintenance burden
- **Rejected because**: Infrastructure and maintenance costs exceed API costs for our scale. Managed API provides better reliability and quality without operational overhead.

### Alternative 5: Azure OpenAI Service
- **Description**: OpenAI models via Microsoft Azure
- **Pros**:
  - Enterprise SLA and support
  - GDPR compliance built-in
  - Integration with Azure ecosystem
  - Same models as OpenAI
  - Regional deployment options
- **Cons**:
  - More expensive than direct OpenAI
  - Requires Azure account setup
  - More complex billing
  - Slower model updates than OpenAI
  - Overkill for simple use case
- **Rejected because**: Enterprise features not needed for this project. Direct Anthropic API provides simpler billing and setup without Azure overhead.

## Consequences

### Positive Consequences
- **Excellent quality**: Claude 3.5 Sonnet produces high-quality, coherent summaries
- **Large context**: 200K tokens handles PDFs up to ~150 pages without chunking
- **Cost-effective**: $3/million input tokens reasonable for PDF summarization
- **Simple integration**: Official Python SDK with good documentation
- **Reliable API**: Production-grade uptime and error handling
- **Caching support**: Claude supports prompt caching (not yet implemented)
- **Future-proof**: Anthropic actively improving models and API

### Negative Consequences
- **API dependency**: Requires internet connectivity and Anthropic availability
- **Cost per request**: Each summary costs ~$0.03-$0.15 depending on size
- **Rate limits**: 10K requests/minute tier (sufficient but requires monitoring)
- **Vendor lock-in**: Switching to another LLM requires code changes
- **No offline mode**: Cannot generate summaries without API access
- **Token limits**: Very large PDFs (>150 pages) may hit context limits

### Neutral Consequences
- **API key required**: Must set `ANTHROPIC_API_KEY` environment variable
- **Error handling**: Need to handle API errors (rate limits, timeouts)
- **Monitoring**: Should track API usage and costs

## Implementation Notes

### Configuration
```python
# src/pdf_summarizer/config.py
DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 1024  # For summary output
```

### API Client Setup
```python
# src/pdf_summarizer/main.py
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### Error Handling
```python
from anthropic import APIError, RateLimitError

try:
    response = client.messages.create(...)
except RateLimitError:
    # Handle rate limit (429)
    log_error("Rate limit exceeded")
except APIError as e:
    # Handle other API errors
    log_error(f"API error: {e}")
```

### Cost Tracking
```python
# Track usage in logs
input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens
cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)
log_api_call(input_tokens, output_tokens, cost)
```

### Code Locations
- Client setup: [src/pdf_summarizer/main.py:89-91](../../src/pdf_summarizer/main.py#L89-L91)
- Summarization function: [src/pdf_summarizer/main.py:162-185](../../src/pdf_summarizer/main.py#L162-L185)
- Configuration: [src/pdf_summarizer/config.py:26](../../src/pdf_summarizer/config.py#L26)

### Dependencies
```toml
# pyproject.toml
dependencies = [
    "anthropic>=0.40.0,<1.0.0",
]
```

## Cost Analysis

### Pricing (as of 2025-11)
- Input: $3 per million tokens
- Output: $15 per million tokens

### Typical Usage
- Average PDF: 15K input tokens, 500 output tokens
- Cost per summary: (15K × $0.000003) + (500 × $0.000015) = $0.045 + $0.0075 = **~$0.05**
- With 60% cache hit rate: **~$0.02 average** (see ADR-0006)

### Cost Comparison
| Provider | Model | Input $/M | Output $/M | Avg Cost/Summary |
|----------|-------|-----------|------------|------------------|
| Anthropic | Claude 3.5 Sonnet | $3 | $15 | $0.05 |
| OpenAI | GPT-4 Turbo | $10 | $30 | $0.16 |
| Google | Gemini 1.5 Pro | $3.50 | $10.50 | $0.058 |
| Cohere | Summarize | $1 | $2 | N/A (too small context) |

## References

- [Anthropic Documentation](https://docs.anthropic.com/)
- [Claude 3.5 Sonnet Model Card](https://www.anthropic.com/claude/sonnet)
- [Anthropic Pricing](https://www.anthropic.com/pricing)
- [Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [API Reference](https://docs.anthropic.com/en/api/messages)

## Related ADRs

- Related to: ADR-0006 (SHA256 Hash-Based Caching) - Cost optimization
- Related to: ADR-0011 (Multi-File Logging Strategy) - API call logging
