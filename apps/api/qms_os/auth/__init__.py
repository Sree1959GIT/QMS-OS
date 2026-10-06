"""Human authentication (R-3; docs/adr/0003-auth-dev-identity.md).

Local accounts with Argon2id passwords and TOTP, server-side sessions, lockout, recovery codes, a CLI first-Admin
bootstrap and dual-control credential resets, with a seam for OIDC identities later. Agents and Telegram principals
never authenticate here. Payload-bound approval (a nonce over the exact payload digest) is a later slice; step-up
is not that.
"""
