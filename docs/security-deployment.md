# LRS-NeuralBlitz deployment security checklist

This is an operational checklist, **not** evidence that a deployment is secure.
It addresses risks observed in the tracked root `docker-compose.yml` on
2026-11-11. Related work: security remediation PR #7 and issue #12.

## 1. Handle previously committed example credentials

The root Compose file on `main` has contained plaintext demonstration
passwords and tokens for InfluxDB, TimescaleDB, and Grafana. Because repository
history retains old values, simply replacing the YAML text does not invalidate
credentials that were ever deployed.

1. Determine whether any committed sample credential or token was used in any
   real environment; document affected systems without writing the secrets into
   issues or logs.
2. Generate distinct, high-entropy replacement credentials using a trusted
   secrets manager or cryptographic password generator.
3. Update service configuration via a local `.env` file (once PR #7 or an
   equivalent environment-variable configuration is deployed). Do not commit
   populated `.env` files.
4. Rotate or revoke the old credentials **in each actual service** and verify
   old-token rejection; changing only Docker environment variables may not
   update credentials persisted in existing service volumes.
5. Check application connections, job configuration and dashboards using the
   service accounts; restart or redeploy as appropriate.
6. If exposures are suspected, follow your incident process and inspect access
   logs while preserving evidence. Avoid copying sensitive logs into tickets.

Never include new secret values in shell history, Git commits, CI logs, PRs or
screenshots. Use an approved secret-management process for production.

## 2. Validate configuration before deployment

Use disposable credentials for test-only validation. With the PR #7
configuration, copy the template into a local file, replace all placeholders,
and verify that no substitution errors remain:

```sh
cp .env.example .env
# Edit .env with disposable test-only values; never commit it.
docker compose config --quiet
```

The `config` command can interpolate sensitive values. Do not paste its full
output into a ticket or CI log. This check proves only that the YAML resolves;
it does **not** prove that initialization, auth, persistence, or services work.

## 3. Restrict attack surface

- Review exposed Compose ports (including 8080, 8086, 5432, 9090, 3000 and
  9100). Bind to `127.0.0.1` for local-only development or deploy behind
  authenticated, firewalled private networking as appropriate.
- Review cAdvisor's `privileged: true` setting and host/device mounts. Remove
  unnecessary privilege and mounts after verifying required metrics.
- Pin reviewed container image versions or digests instead of relying on
  mutable `latest` tags; integrate a vulnerability scanning/update process.
- Use least-privilege service identities, restrict sensitive data volumes, and
  disable or firewall admin endpoints that are not needed.
- Do not interpret `depends_on` as proof of service readiness. Validate actual
  health and authentication before allowing client operations.

## 4. Runtime failure checks

Before declaring an NBOS backend operational, test at least:

- No backend reachable: boot and execution must fail, not return mock success.
- HTTP error and `ok: false` response: client must surface failure and remain
  disconnected.
- Debug, status and introspection endpoints unavailable: no fabricated runtime,
  governance or attestation values may be presented as live evidence.
- Recovery: successful operations should occur only after the real backend is
  healthy and properly authenticated.

PR #7 attempts the fail-closed client change; validate with a real test harness
before merging or treating the behavior as verified.

## 5. Release gate

- [ ] No live credentials in tracked files or build artifacts.
- [ ] Previously used exposed credentials rotated/revoked and checked.
- [ ] Configuration validated with non-production secrets.
- [ ] Exposed ports and privileged mounts reviewed for deployment context.
- [ ] Image versions pinned and scanned.
- [ ] Client failure-path tests pass.
- [ ] Monitoring works without inventing telemetry or runtime state.
- [ ] Security contact and incident escalation route confirmed.
