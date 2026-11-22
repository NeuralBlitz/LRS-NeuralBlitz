# Root Compose security CI baseline

The root Compose file is a local development/monitoring configuration.
The CI check in `scripts/check_compose_security.py` invokes Docker Compose
with **disposable values only** and tests its normalized JSON output.

It checks **both** the default Compose service set and the `host-metrics` opt-in profile, without starting containers. Privileged cAdvisor must not be enabled in the default profile.

It prevents the following regressions:
- The five default and one opt-in host-metrics monitoring/database service ports accidentally
  binding to all host interfaces rather than `127.0.0.1`.
- Changing the current published port mapping or adding a new published port.
- Hardcoding service credentials in place of the required injected values.
- Adding new privileged services.
- Introducing or changing mutable `:latest` image references beyond the
  explicitly recorded legacy references.

Run locally from the root with Docker Compose installed:

```sh
python3 scripts/check_compose_security.py
```

The checker captures Compose output and never prints the interpolated JSON.
It does not connect to or provision containers, rotate any credentials,
verify live authentication, scan repository history, or prove a deployment
is secure.

**Still unresolved:** opt-in cAdvisor still uses privileged mode and sensitive
host mounts; five existing image references contain mutable `latest`
tags (one has a `latest-pg15` suffix); and operator-side credential
rotation is required for any real deployment that ever used committed
defaults. The exceptions prevent additional drift but are not approvals.
Track and resolve them under issue #12. Bind-address overrides can still be
used for intentional external access; those deployments require separate
network/security review.

To explicitly enable high-privilege host metrics on a **trusted development host**, use `docker compose --profile host-metrics up -d` after reviewing the mounts and its privileged access. Never treat opt-in as production approval. Default `docker compose up -d` omits cAdvisor.
