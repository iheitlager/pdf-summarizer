# ADR-0006: SHA256 Hash-Based Caching Mechanism

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: Cost optimization for Claude API calls

## Context

The PDF Summarizer sends uploaded PDFs to Anthropic's Claude API for summarization. API costs are based on token usage, and processing the same document multiple times incurs redundant costs.

### Problem
- Users may upload the same PDF multiple times (intentionally or accidentally)
- Different users may upload identical documents
- Each Claude API call costs money based on input tokens
- Processing time is wasted on duplicate content
- No way to detect duplicate files by filename alone (users rename files)

### Observations
- Identical PDF files have identical byte-level content
- SHA256 hash uniquely identifies file content (collision probability: ~10^-77)
- Summaries for identical documents are identical
- Users benefit from instant results on duplicate uploads

### Cost Impact
Initial analysis showed potential **60% cost reduction** for environments with document reuse (e.g., team sharing reports, educational content).

## Decision

Implement **SHA256 hash-based caching** to detect and reuse summaries for duplicate PDF files.

### Mechanism
1. **Hash Calculation**: Compute SHA256 hash of uploaded PDF content
2. **Cache Lookup**: Query database for existing upload with same hash
3. **Cache Hit**: If found, reuse existing summary without API call
4. **Cache Miss**: If not found, process with Claude API and store with hash
5. **Cross-Session**: Cache works across all user sessions (global deduplication)

### Implementation
- Store `file_hash` (VARCHAR(64)) in Upload table
- Index `file_hash` for fast lookups
- Store `is_cached` (BOOLEAN) flag to track cache hits
- Allow duplicate hash values (same file uploaded by different users)
- Display cache status in UI with visual indicator

### Database Schema
```sql
CREATE TABLE upload (
    id INTEGER PRIMARY KEY,
    file_hash VARCHAR(64) INDEXED,  -- SHA256 hash for deduplication
    is_cached BOOLEAN DEFAULT FALSE, -- Track cache hits
    ...
);
```

## Alternatives Considered

### Alternative 1: Filename-Based Deduplication
- **Description**: Use filename to detect duplicates
- **Pros**:
  - Simple to implement
  - No hash computation needed
  - Fast lookup
- **Cons**:
  - Unreliable: Users rename files
  - False positives: Different files with same name
  - No content verification
  - Per-user only (can't detect cross-user duplicates)
- **Rejected because**: Filenames are not reliable identifiers for content. Same filename can have different content, and users frequently rename files.

### Alternative 2: MD5 Hash
- **Description**: Use faster MD5 hash instead of SHA256
- **Pros**:
  - Faster computation than SHA256
  - Shorter hash (128-bit vs 256-bit)
- **Cons**:
  - Cryptographically broken (collision attacks exist)
  - Not recommended for new systems
  - Marginal speed benefit for small files
- **Rejected because**: SHA256 is the modern standard and provides better security guarantees. Performance difference is negligible for PDF files under 10MB.

### Alternative 3: Per-User Caching Only
- **Description**: Cache based on session_id + hash combination
- **Pros**:
  - Privacy: Users only see their own cached results
  - Simpler to reason about
- **Cons**:
  - Misses cost savings from cross-user duplication
  - Reduced cache hit rate
  - Still requires hash computation
- **Rejected because**: PDFs don't contain private data (summaries are generated, not extracted). Global caching maximizes cost savings. Cache status is displayed to users.

### Alternative 4: No Caching
- **Description**: Process every upload with Claude API
- **Pros**:
  - Simplest implementation
  - Always fresh results
  - No storage overhead
- **Cons**:
  - High API costs for duplicate uploads
  - Slower user experience (always waits for API)
  - Wasted API quota
  - Environmental impact (redundant computation)
- **Rejected because**: Cost optimization is a primary goal. Caching provides significant cost savings with minimal complexity.

### Alternative 5: Time-Based Cache Expiration
- **Description**: Expire cached summaries after X days
- **Pros**:
  - Could handle changing summarization models
  - Limits cache growth
- **Cons**:
  - PDFs don't change (content is immutable)
  - Summaries don't become "stale"
  - Unnecessary complexity
  - Loses cost savings over time
- **Rejected because**: PDF content is immutable. A summary from last month is just as valid as one from yesterday. Cache indefinitely until file is deleted.

## Consequences

### Positive Consequences
- **60% cost reduction**: Eliminates redundant API calls for duplicate files
- **Faster responses**: Cache hits return instantly (no API latency)
- **Cross-user benefits**: All users benefit from others' uploads
- **Transparent**: UI shows cache status with badge indicator
- **Accurate**: SHA256 ensures content-based matching (not filename)
- **API quota savings**: Preserves API rate limits for unique content
- **Environmental**: Reduces unnecessary computation

### Negative Consequences
- **Storage overhead**: 64 bytes per upload for hash storage (minimal)
- **Hash computation**: ~10-50ms CPU time per upload (acceptable)
- **Database queries**: Additional lookup query before processing (indexed, fast)
- **Privacy consideration**: Users can detect if others uploaded same file (mitigated by showing cache status)
- **Stale summaries**: If Claude model changes, old summaries remain (acceptable trade-off)

### Neutral Consequences
- **Cache invalidation**: No automatic expiration (PDFs are immutable)
- **Hash collisions**: Theoretical possibility (probability: 1 in 10^77)
- **Database growth**: Hash storage adds 64 bytes per upload

## Implementation Notes

### Hash Calculation
```python
# In utils.py
def calculate_file_hash(file_data: bytes) -> str:
    """Calculate SHA256 hash of file content."""
    return hashlib.sha256(file_data).hexdigest()
```

### Cache Lookup
```python
# In main.py
def find_existing_summary_by_hash(file_hash: str) -> Optional[Summary]:
    """Check if summary exists for this file hash."""
    existing_upload = Upload.query.filter_by(file_hash=file_hash).first()
    if existing_upload and existing_upload.summaries:
        return existing_upload.summaries[0]
    return None
```

### Cache Hit Handling
```python
cached_summary = find_existing_summary_by_hash(file_hash)
if cached_summary:
    # Reuse existing summary
    new_upload.is_cached = True
    log_cache_hit(file_hash)
else:
    # Process with Claude API
    new_upload.is_cached = False
    log_cache_miss(file_hash)
```

### Code Locations
- Hash calculation: [src/pdf_summarizer/utils.py:15-20](../../src/pdf_summarizer/utils.py#L15-L20)
- Cache lookup: [src/pdf_summarizer/main.py:152-160](../../src/pdf_summarizer/main.py#L152-L160)
- Upload model: [src/pdf_summarizer/main.py:96-98](../../src/pdf_summarizer/main.py#L96-L98)

### Database Impact
- Index on `file_hash` ensures fast lookups (O(log n))
- Query: `SELECT * FROM upload WHERE file_hash = ? LIMIT 1`
- Typical lookup time: < 1ms

### UI Indication
Cache hits display badge on results page:
```html
{% if upload.is_cached %}
  <span class="badge bg-success">Cached</span>
{% endif %}
```

## Metrics

### Cache Hit Rate Tracking
```python
total_uploads = Upload.query.count()
cache_hits = Upload.query.filter_by(is_cached=True).count()
cache_rate = (cache_hits / total_uploads) * 100
```

### Cost Savings
Assuming $0.003 per 1K input tokens, average PDF ~20K tokens:
- Cost per summary: ~$0.06
- With 60% cache hit rate: **36% cost reduction**
- 1000 uploads: Save ~$21.60

## References

- [SHA256 Specification](https://en.wikipedia.org/wiki/SHA-2)
- [Content-Based Deduplication](https://en.wikipedia.org/wiki/Data_deduplication#Content-based_deduplication)
- [Anthropic Pricing](https://www.anthropic.com/pricing)
- [Database Schema](../database.md#caching-mechanism)

## Related ADRs

- Related to: ADR-0002 (SQLite with SQLAlchemy ORM)
- Related to: ADR-0004 (Use Anthropic Claude API)
- Related to: ADR-0007 (Session-Based User Tracking)
