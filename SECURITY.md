# Security Policy

NeuralBlitz/LRS-NeuralBlitz accepts responsible vulnerability reports. Please do not
publish exploit details, credentials, personal information, or working attack code
in a public issue or pull request.

## Reporting a vulnerability

1. Check the repository **Security** tab for **Report a vulnerability**. If the
   private vulnerability-reporting feature is available, use it to submit details.
2. If that private feature is unavailable, use an established private contact
   channel with the repository maintainers. Do **not** post confidential details
   in public issues merely because a private reporting channel is unavailable.
3. Include the affected commit/version, component, prerequisites, observed
   behavior, impact, and minimal safe reproduction steps. Redact all secrets.

The maintainers will assess submissions and coordinate remediation and
disclosure. No response-time or remediation-time guarantee is currently
established; a formal service-level target should be published when the
maintainers have confirmed operational capacity.

## Supported versions

The repository previously listed 5.1.x and 4.0.x as supported, but that
information has not been revalidated as part of the current repository audit.
Do not infer active security-maintenance coverage from an old version table.
Confirm maintained releases and security backport policy with the maintainers
before relying on a version in production.

## Deployment and credential safety

- Never commit passwords, API tokens, authentication headers, or populated
  local `.env` files.
- Historical committed credentials are **not** made safe by merely changing
  the current configuration. Rotate any such credentials actually used in
  deployed environments, then revoke old values.
- Treat Docker Compose examples as development templates until network
  exposure, container privileges, image versions, and secret handling
  have been reviewed.
- Run an explicitly configured test deployment and verify authentication
  failures before exposing any service.

See [Security deployment checklist](docs/security-deployment.md) for
operator validation and incident-response steps.
