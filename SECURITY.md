# Security Policy

## Supported Versions

Security updates are provided for the following versions of this repository. Only the latest stable release receives active security patches and vulnerability fixes.

| Version | Supported          | Notes |
|---------|--------------------|-------|
| `main`  | :white_check_mark: | Latest development branch; receives all security updates |
| `v1.0.0`| :x:                | No longer supported |

> **Note**: We recommend always using the latest version to benefit from security improvements and bug fixes.

---

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in this project, please report it **privately** using GitHub's built-in private vulnerability reporting feature.

### How to Report:
1. Go to the repository's main page: [https://github.com/H0NEYP0T-466/linkedin-agent](https://github.com/H0NEYP0T-466/linkedin-agent)
2. Click on **"Security"** in the top navigation
3. Select **"Report a vulnerability"**
4. Fill out the form with as much detail as possible (affected components, steps to reproduce, impact, etc.)
5. Submit the report

> 🔒 Your report will be handled privately by the maintainers. Public discussion is disabled until a fix is prepared.

Do **not** disclose the vulnerability publicly before a patch has been released.

---

## Disclosure Policy

We follow a **responsible disclosure** timeline:

- Upon receiving a valid vulnerability report, we will:
  - Acknowledge receipt within **48 hours**
  - Conduct initial triage and assign priority within **7 days**
  - Develop and test a fix within **14 days** (depending on severity)
  - Release a public advisory and update the codebase within **30 days**

Public disclosure occurs only after:
- A fix has been developed and tested
- The vulnerable version(s) are no longer actively maintained (if applicable)
- Coordinated release timing with stakeholders (if needed)

We appreciate researchers who responsibly disclose vulnerabilities and work with them throughout the process.

---

## Security Response Process

After you submit a vulnerability report via GitHub's private reporting system:

1. **Acknowledgment (within 48 hours)**  
   You’ll receive an automated confirmation and a maintainer may reach out for clarification.

2. **Triage & Assessment (within 7 days)**  
   The security team reviews the report, validates the issue, and classifies its severity (Low/Medium/High/Critical).

3. **Fix Development (within 14 days)**  
   A patch or mitigation strategy is developed and tested internally.

4. **Coordination & Disclosure (within 30 days)**  
   - Fix is merged into `main`
   - Public advisory is published (if appropriate)
   - CVE may be requested if warranted
   - Researcher is credited (with permission)

5. **Follow-up**  
   Users are notified via release notes and changelogs when fixes are available.

---

## Out of Scope

The following are **not considered security vulnerabilities** and will not be addressed:

- Social engineering attacks (e.g., phishing users)
- Denial-of-service via legitimate API usage (rate-limited endpoints)
- Third-party services (LinkedIn, GitHub, Telegram, OpenAI/LongCat API) — their security is outside our control
- Misconfiguration by end users (e.g., exposing API keys in environment variables)
- Issues arising from running untrusted third-party code in user environments
- Bugs that do not lead to unauthorized access, data leakage, or remote code execution

> ⚠️ **Important**: This tool interacts with external platforms (GitHub, LinkedIn, Telegram). Ensure you comply with their Terms of Service and rate limits. Unauthorized automation may violate platform policies.

---

## Security Best Practices

To use this application securely:

- **Never commit sensitive data** (API keys, tokens, credentials) to version control
- Use `.env` files (added to `.gitignore`) for environment variables
- Run the backend behind a firewall or authentication layer in production
- Keep dependencies updated (`pip install --upgrade -r backend/requirements.txt`, `npm audit`, `npm update`)
- Monitor logs for unusual activity
- Use strong, unique passwords and rotate secrets regularly
- Enable 2FA wherever possible (GitHub, Telegram, etc.)

---

Thank you for helping keep this project secure!