# ADR-0014: Implement SBOM Generation and Security Scanning

**Status**: Accepted

**Date**: 2025-01-18

**Deciders**: Ilja Heitlager

**Technical Story**: feat/sbom - Add comprehensive Software Bill of Materials generation and security vulnerability scanning

## Context

Modern software supply chain security requires transparency about dependencies and proactive vulnerability management. As the PDF Summarizer project grows and potentially moves toward production deployment, we need:

1. **Transparency**: Clear visibility into all dependencies (direct and transitive)
2. **Vulnerability Detection**: Automated scanning for known security vulnerabilities
3. **Compliance**: Industry-standard SBOM format for security audits and compliance requirements
4. **Continuous Monitoring**: Regular checks for newly discovered vulnerabilities
5. **Supply Chain Security**: Better understanding of our software supply chain risks

The project uses `uv` as the package manager with `pyproject.toml`, which presents unique challenges as many SBOM tools are built for traditional pip/requirements.txt workflows.

**Current State:**
- 9 production dependencies + 10 development dependencies
- No automated vulnerability scanning
- No SBOM generation capability
- GitHub Dependabot configured but using "pip" ecosystem (may need adjustment for uv)
- Existing CI/CD with GitHub Actions

**Pain Points:**
- No visibility into transitive dependencies
- Manual process to check for vulnerabilities
- No standardized format for dependency reporting
- Difficult to comply with security audit requirements

## Decision

Implement SBOM generation using **CycloneDX format** with the following tools:

1. **Primary Tool: cyclonedx-bom** (Python library)
   - Generates CycloneDX JSON format SBOM
   - Added as development dependency

2. **Security Scanning: pip-audit** (PyPA official tool)
   - Scans dependencies against OSV vulnerability database
   - Added as development dependency
   - Official Python Packaging Authority (PyPA) tool

3. **CI/CD Integration:**
   - New workflow: `.github/workflows/sbom-check.yml`
   - Weekly scheduled runs (Mondays at midnight UTC)
   - Manual trigger capability
   - Artifact upload with 90-day retention
   - Added security audit step to PR checks

4. **Makefile Commands:**
   - `make sbom` - Generate SBOM only
   - `make audit` - Run security audit only
   - `make sbom-check` - Generate both SBOM and security report

**Implementation Approach:**
- Export dependencies using `uv pip freeze` to temporary requirements.txt
- Generate SBOM from requirements.txt using cyclonedx-bom
- Clean up temporary files automatically
- Store artifacts in gitignored sbom.json and security-report.json

## Alternatives Considered

### Alternative 1: SPDX Format with spdx-tools

- **Description**: Use SPDX (Software Package Data Exchange) format instead of CycloneDX
- **Pros**:
  - ISO/IEC 5962 standard
  - Broader adoption in open source community
  - Good for license compliance
- **Cons**:
  - Less focused on security use cases
  - Fewer vulnerability scanning integrations
  - Python tooling less mature than cyclonedx-bom
  - More complex format for our needs
- **Rejected because**: CycloneDX is better suited for security-focused SBOM with better vulnerability scanning tool integration

### Alternative 2: Syft + Grype (Anchore)

- **Description**: Use Syft for SBOM generation and Grype for vulnerability scanning
- **Pros**:
  - Language-agnostic (works with any project type)
  - Can scan Docker images directly
  - Generates both SPDX and CycloneDX formats
  - Strong vulnerability database
- **Cons**:
  - External binary dependencies (not Python packages)
  - Requires separate installation (not via uv/pip)
  - Overkill for Python-only project
  - More complex to integrate into existing workflow
- **Rejected because**: Too heavyweight for current needs; consider for future when adding container scanning

### Alternative 3: Trivy (Aqua Security)

- **Description**: Use Trivy for comprehensive security scanning including SBOM
- **Pros**:
  - All-in-one solution (SBOM + vulnerabilities + misconfigurations + secrets)
  - Excellent Docker image scanning
  - Fast and comprehensive
  - Good CI/CD integration
- **Cons**:
  - External binary (not Python package)
  - Heavy dependency for simple Python project
  - Requires learning new tool ecosystem
  - More suited for container-based deployments
- **Rejected because**: Too heavyweight for current needs; may revisit when Docker deployment becomes primary focus

### Alternative 4: Dependency-Track (OWASP)

- **Description**: Self-hosted SBOM management platform
- **Pros**:
  - Continuous monitoring and alerting
  - Policy engine
  - Centralized SBOM repository
  - Audit log and reporting
- **Cons**:
  - Requires infrastructure (server/database)
  - Additional operational overhead
  - Overkill for single-project setup
  - Significant setup complexity
- **Rejected because**: Too complex for current project scale; consider for future if managing multiple projects

### Alternative 5: GitHub Dependency Graph Only

- **Description**: Rely solely on GitHub's built-in dependency scanning
- **Pros**:
  - Zero setup required
  - Free for public repositories
  - Automatic Dependabot alerts
  - Native GitHub integration
- **Cons**:
  - No portable SBOM file
  - Limited to GitHub ecosystem
  - No local SBOM generation
  - Cannot customize scanning behavior
  - No control over scanning schedule
- **Rejected because**: Need portable SBOM files for compliance and local scanning capability

## Consequences

### Positive Consequences

- **Transparency**: Complete visibility into all dependencies (direct and transitive)
- **Security**: Automated vulnerability detection on every PR and weekly
- **Compliance**: Industry-standard CycloneDX SBOM format for audits
- **Cost**: Minimal overhead (Python packages, no infrastructure needed)
- **Integration**: Seamless integration with existing uv/pyproject.toml workflow
- **Artifacts**: SBOM files preserved as GitHub Actions artifacts (90-day retention)
- **Portability**: SBOM files can be used with external security tools
- **Developer Experience**: Simple Makefile commands for local use
- **CI/CD**: Minimal changes to existing workflows

### Negative Consequences

- **Temporary Files**: Requires temporary requirements.txt export (cleaned up automatically)
- **uv Ecosystem**: Tools don't natively support uv.lock format yet (workaround required)
- **Maintenance**: Two additional development dependencies to maintain
- **False Positives**: May generate vulnerability alerts that require investigation
- **CI/CD Time**: Adds ~30-60 seconds to CI/CD pipeline runtime

### Neutral Consequences

- **Format Choice**: Committed to CycloneDX format (though widely supported)
- **Tool Ecosystem**: Using Python-native tools (may need different tools for Docker scanning later)
- **Scheduled Runs**: Weekly schedule adds minimal GitHub Actions minutes usage
- **Learning Curve**: Team needs to understand SBOM format and vulnerability reports

## Implementation Notes

### Files Modified

1. **pyproject.toml**:
   ```toml
   [dependency-groups]
   dev = [
       # ... existing deps ...
       "cyclonedx-bom>=4.0.0",
       "pip-audit>=2.6.0",
   ]
   ```

2. **Makefile**: Added targets `sbom`, `audit`, `sbom-check`

3. **.gitignore**: Added `sbom*.json`, `security-report.json`, `requirements.txt`

4. **.github/workflows/sbom-check.yml**: New workflow for scheduled SBOM generation

5. **.github/workflows/pr-checks.yml**: Added security audit step

6. **README.md**: Added SBOM section under Security Features

7. **CLAUDE.md**: Added SBOM commands and documentation

8. **CHANGELOG.md**: Version 0.4.3 entry documenting all changes

### Dependencies Added

- `cyclonedx-bom>=4.0.0` - SBOM generation
- `pip-audit>=2.6.0` - Security vulnerability scanning

### Workflow Details

**Weekly SBOM Check** (`.github/workflows/sbom-check.yml`):
- Trigger: Weekly (Monday 00:00 UTC), PR, push to main, manual
- Steps: Setup → Install deps → Generate SBOM → Security audit → Upload artifacts
- Artifacts: sbom.json, security-report.json (90-day retention)
- Job summary: Reports component count and vulnerability status

**PR Security Check** (`.github/workflows/pr-checks.yml`):
- Added security audit step (continue-on-error: true)
- Runs pip-audit on every PR
- Non-blocking (warns but doesn't fail build)

### Generated Files

1. **sbom.json** (CycloneDX format):
   - JSON format
   - Lists all components (dependencies)
   - Includes version information
   - Contains dependency tree
   - File size: ~10-50KB typically

2. **security-report.json** (pip-audit format):
   - JSON format
   - Lists vulnerabilities found
   - Includes CVE IDs, severity, affected versions
   - Remediation advice
   - Only created by `make sbom-check`

### Usage

```bash
# Local development
make sbom         # Generate SBOM
make audit        # Check for vulnerabilities
make sbom-check   # Both

# CI/CD
# Automatic on PR (security audit)
# Automatic weekly (full SBOM + audit)
# Manual trigger via GitHub Actions UI
```

## References

- [CycloneDX Specification](https://cyclonedx.org/)
- [cyclonedx-bom GitHub](https://github.com/CycloneDX/cyclonedx-python)
- [pip-audit Documentation](https://pypi.org/project/pip-audit/)
- [OWASP Software Component Verification Standard](https://owasp.org/www-project-software-component-verification-standard/)
- [NIST SP 800-218 SSDF - Software Supply Chain Security](https://csrc.nist.gov/publications/detail/sp/800-218/final)
- [Open Source Vulnerability (OSV) Database](https://osv.dev/)

## Related ADRs

- Related to: ADR-0003 (Use uv as Package Manager) - SBOM tools must work with uv ecosystem
- Related to: ADR-0013 (Use Ruff and Black) - SBOM adds to development dependencies
- May inform future ADR: Container SBOM scanning when Docker deployment is primary focus
