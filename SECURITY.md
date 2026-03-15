# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | Yes                |

## Reporting a Vulnerability

If you discover a security issue in OpenCadence, please report it responsibly.

**Do not open a public GitHub issue for security concerns.**

Instead, please email: **security@letter22.io**

### What to include

- Description of the issue
- Steps to reproduce (if applicable)
- Potential impact
- Suggested fix (if any)

### Response timeline

- **Acknowledgment**: within 48 hours
- **Initial assessment**: within 5 business days
- **Fix timeline**: depends on severity, typically within 30 days for critical issues

### Process

1. Report is received and acknowledged
2. Issue is confirmed and assessed for severity
3. A fix is developed and tested
4. A security advisory is published alongside the fix release
5. Reporter is credited (unless they prefer anonymity)

## Security Practices

- Dependencies are monitored via Dependabot
- Static analysis is performed via CodeQL on every PR
- All data in transit is encrypted via TLS
- API keys are stored as bcrypt hashes
- No PII is stored in the default schema
