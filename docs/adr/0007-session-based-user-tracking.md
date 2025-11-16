# ADR-0007: Session-Based User Tracking Without Authentication

**Status**: Accepted

**Date**: 2025-11-16

**Technical Story**: User tracking for personalized upload history and rate limiting

## Context

The PDF Summarizer needs to:
- Track which uploads belong to which user
- Display "My Uploads" page showing user's own uploads
- Implement rate limiting per user (10 uploads/hour, 200 requests/day)
- Provide personalized experience without requiring registration
- Support caching across all users (global cache)

### Requirements
- Identify individual users across page requests
- Persist user identity for reasonable duration (weeks, not hours)
- No user registration or password management
- No personal data collection (privacy-friendly)
- Simple to implement and maintain
- Work for anonymous users

### Anti-Requirements
- **No authentication**: Application is for casual use, not sensitive data
- **No user accounts**: Avoid registration friction
- **No password management**: Avoid security liability

## Decision

Use **session-based user tracking with UUID identifiers** without authentication.

### Mechanism
1. **Session ID Generation**: Create UUID v4 on first visit
2. **Storage**: Store in Flask session cookie (signed, HTTP-only)
3. **Lifetime**: 30-day persistent session
4. **Database Tracking**: Store `session_id` with each upload
5. **Privacy**: No personal information collected

### Implementation
```python
def get_or_create_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        session.permanent = True  # 30-day lifetime
    return session["session_id"]
```

### Session Cookie Properties
- **Signed**: Flask SECRET_KEY prevents tampering
- **HTTP-only**: JavaScript cannot access (XSS protection)
- **Persistent**: 30-day lifetime (configurable)
- **No personal data**: UUID is randomly generated, not tied to identity

## Alternatives Considered

### Alternative 1: IP Address Tracking
- **Description**: Use client IP address to identify users
- **Pros**:
  - No cookies required
  - Works across browsers
  - Simple implementation
- **Cons**:
  - NAT: Multiple users share same IP (corporate, family networks)
  - Dynamic IPs: User's IP changes (mobile, DHCP)
  - VPN/Proxy: IP changes frequently
  - Privacy concerns: IP addresses can identify individuals
  - Inaccurate for rate limiting
- **Rejected because**: IP addresses are unreliable identifiers. Multiple users behind NAT would share quota, and mobile users would lose history when IP changes.

### Alternative 2: Username/Password Authentication
- **Description**: Traditional user accounts with login
- **Pros**:
  - Accurate user identification
  - Works across devices
  - Industry standard
- **Cons**:
  - Registration friction (many users leave)
  - Password management liability (security risk)
  - Forgot password flow needed
  - Email verification required
  - Privacy concerns (collecting email addresses)
  - Significant development complexity
  - Overkill for PDF summarization
- **Rejected because**: Authentication is unnecessary complexity for a simple PDF summarization tool. No sensitive data to protect. Registration would deter casual users.

### Alternative 3: OAuth (Google, GitHub, etc.)
- **Description**: Third-party authentication providers
- **Pros**:
  - No password management
  - Trusted providers
  - Single sign-on
- **Cons**:
  - Requires user has Google/GitHub account
  - External dependency (provider outage = app broken)
  - Privacy concerns (tracking by provider)
  - OAuth setup complexity
  - Rate limits on OAuth APIs
  - Still requires registration flow
- **Rejected because**: Adds external dependency and still requires users to log in. Unnecessary friction for casual use.

### Alternative 4: Browser Fingerprinting
- **Description**: Identify users by browser characteristics (User-Agent, screen size, fonts, etc.)
- **Pros**:
  - No cookies needed
  - Works without user interaction
- **Cons**:
  - Privacy invasion (tracking without consent)
  - Unreliable (characteristics change with browser updates)
  - Easily defeated by privacy tools
  - Ethical concerns
  - May violate privacy regulations (GDPR)
- **Rejected because**: Ethically questionable and technically unreliable. Privacy-invasive without user consent.

### Alternative 5: No User Tracking
- **Description**: Treat every request as anonymous
- **Pros**:
  - Maximum privacy
  - Simplest implementation
  - No state management
- **Cons**:
  - Cannot implement "My Uploads" feature
  - Cannot do per-user rate limiting
  - Poor user experience (no history)
  - Users can't find their previous uploads
- **Rejected because**: Rate limiting and upload history are core features. Need some form of user identification.

### Alternative 6: Local Storage (Browser-Side)
- **Description**: Store session ID in browser localStorage
- **Pros**:
  - No server-side session management
  - Persists longer than cookies
- **Cons**:
  - Accessible by JavaScript (XSS vulnerability)
  - Doesn't work with JavaScript disabled
  - Per-domain only (no cross-domain)
  - Harder to implement rate limiting server-side
- **Rejected because**: Less secure than HTTP-only cookies. Server-side session management is simpler for rate limiting.

## Consequences

### Positive Consequences
- **Frictionless**: Users start using immediately, no registration
- **Privacy-friendly**: No personal data collected, just random UUID
- **Persistent**: 30-day sessions provide continuity
- **Secure**: Signed cookies prevent tampering
- **Simple**: No password reset, email verification, or user management
- **Effective rate limiting**: Per-session quotas prevent abuse
- **Personalization**: "My Uploads" shows user's own history
- **Cross-session caching**: Global cache benefits all users

### Negative Consequences
- **Browser-specific**: Clearing cookies loses history
- **No cross-device**: Session doesn't follow user to different devices
- **Abuse potential**: User can clear cookies to bypass rate limits (mitigated by IP-based backup)
- **No account recovery**: Losing session means losing history (acceptable for this use case)
- **No sharing**: Users can't share uploads with specific others (acceptable)

### Neutral Consequences
- **Cookie consent**: May need cookie banner in some jurisdictions (low-priority)
- **Session storage**: Flask sessions stored in cookies (< 4KB limit)
- **State management**: Flask session handling is built-in

## Implementation Notes

### Session Configuration
```python
# In config.py
PERMANENT_SESSION_LIFETIME = timedelta(days=30)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# In main.py
session.permanent = True  # Enable 30-day lifetime
```

### Session ID Generation
```python
def get_or_create_session_id():
    """Get or create a unique session ID for the user"""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        session.permanent = True
        app.logger.info(f"New session created: {session['session_id'][:8]}...")
    return session["session_id"]
```

### Database Integration
```python
# Upload model includes session_id
class Upload(db.Model):
    session_id = db.Column(db.String(255), index=True)  # Indexed for fast queries
```

### Querying User's Uploads
```python
# Get current user's uploads
session_id = get_or_create_session_id()
my_uploads = Upload.query.filter_by(session_id=session_id)\
                         .order_by(Upload.upload_date.desc())\
                         .all()
```

### Rate Limiting
```python
# Flask-Limiter uses get_remote_address by default
# Can combine with session_id for stricter limiting
@limiter.limit("10 per hour")
def upload_route():
    session_id = get_or_create_session_id()
    # Check session-specific rate limits
```

### Code Locations
- Session management: [src/pdf_summarizer/main.py:144-150](../../src/pdf_summarizer/main.py#L144-L150)
- Upload model: [src/pdf_summarizer/main.py:99](../../src/pdf_summarizer/main.py#L99)
- My Uploads route: [src/pdf_summarizer/main.py:375-391](../../src/pdf_summarizer/main.py#L375-L391)

## Security Considerations

### Cookie Security
- **Signed**: Flask SECRET_KEY prevents tampering
- **HTTP-only**: JavaScript cannot access (XSS protection)
- **Secure flag**: Use HTTPS in production (not set by default for dev)
- **SameSite**: Set to 'Lax' to prevent CSRF

### Session Hijacking
- Low risk: No sensitive operations or data
- Mitigation: Use HTTPS in production
- Impact: Attacker could see victim's upload history (not sensitive)

### Privacy
- No personal data collected
- UUID cannot identify real user
- Can be cleared by user at any time
- No tracking across domains

## User Experience

### New User Flow
1. User visits homepage
2. UUID automatically created
3. User uploads PDF → associated with UUID
4. User can see "My Uploads" page

### Returning User Flow
1. Cookie still valid (< 30 days)
2. Previous uploads visible in "My Uploads"
3. Personalized homepage shows recent uploads

### Cookie Cleared
1. Session lost, new UUID created
2. Old uploads still exist but not visible
3. User starts fresh (acceptable trade-off)

## References

- [Flask Sessions](https://flask.palletsprojects.com/en/3.0.x/api/#sessions)
- [UUID RFC 4122](https://datatracker.ietf.org/doc/html/rfc4122)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [Database Schema](../database.md#session-management)

## Related ADRs

- Related to: ADR-0002 (SQLite with SQLAlchemy ORM)
- Related to: ADR-0006 (SHA256 Hash-Based Caching)
- Related to: ADR-0010 (Flask-Limiter for Rate Limiting)
