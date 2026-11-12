# RoadSentinel – Production target architecture (roadmap)

> **Everything on this page is NOT implemented.** It describes how the hackathon foundation
> should evolve before any operational use. What is implemented today is documented in
> [SECURITY.md](SECURITY.md).

## Key management – NOT IMPLEMENTED

* Replace `EnvKeyProvider` with a `KeyProvider` backed by a KMS or HSM (HashiCorp Vault Transit,
  AWS KMS / CloudHSM, Azure Key Vault Managed HSM, or a national-police HSM). The interface
  (`wrap`, `unwrap`, `current_version`) is already in place.
* Automatic master-key rotation with scheduled re-wrap jobs; DEK rotation per tenant on a
  schedule plus lazy re-encryption of evidence files.
* Separate keys per purpose and data class (evidence, PII fields, blind index), with dual
  control (two-person rule) on key administration.
* Crypto-shredding: destroying a tenant's DEK renders retained ciphertext unreadable.

## Identity – NOT IMPLEMENTED

* SSO via OpenID Connect against the police identity provider (Keycloak, Entra ID, national IdP),
  with phishing-resistant MFA (FIDO2/passkeys, smart cards) and SCIM provisioning.
* Service accounts for the detection pipeline: mTLS client certificates or workload identity,
  scoped to "create alert / ingest evidence" for one tenant.
* Adaptive (risk-based) authentication: new device, impossible travel, unusual hours, anomalous
  evidence access → step-up or block.
* Device binding of sessions (DPoP / token binding).

## Authorization – NOT IMPLEMENTED

* Externalize policies to OPA (Rego) or AWS Cedar, versioned and tested in CI; ABAC attributes
  such as case assignment, shift, jurisdiction and clearance.
* Just-in-time elevation for administrators with automatic expiry.

## Network and platform – NOT IMPLEMENTED

* WAF and DDoS protection in front of Caddy; private connectivity (VPN / police network) for
  patrol devices; mTLS between services; separate DB host with encrypted volumes.
* Kubernetes or hardened VMs with signed images (cosign), SBOM generation, admission policies,
  read-only filesystems and seccomp profiles everywhere (including the proxy).
* Redis-backed distributed rate limiting; horizontal scaling of the API.
* Encrypted, immutable backups with tested restore procedures.

## Monitoring and audit – NOT IMPLEMENTED

* SIEM export of audit and security events (syslog/CEF or OpenTelemetry), with alert rules for
  cross-tenant probes, refresh-token reuse, lockouts and mass evidence access.
* Periodic anchoring of each tenant's audit head hash to WORM storage or an external timestamping
  authority (RFC 3161), closing the tail-truncation gap.
* Ed25519 signatures over evidence hashes at ingestion (chain of custody) with a verification
  endpoint.

## GDPR and Directive (EU) 2016/680 – NOT IMPLEMENTED (organizational + technical)

* Documented legal basis and purpose limitation per processing activity; Data Protection
  Impact Assessment before deployment; DPO sign-off.
* Retention: automatic deletion of video without an incident after a short period (e.g. 72 h),
  configurable per tenant; legal holds for case evidence.
* Logging obligations of Art. 25 of the Directive (collection, alteration, consultation,
  disclosure, combination, erasure) mapped to audit actions; log retention policy.
* Data-subject rights handling and disclosure workflows; records of processing activities.
* Faces and plates blurred by default in all general searches (implemented for evidence views
  today; must extend to natural-language archive search when it exists).
* Field validation of detection accuracy (night, rain, dense traffic) before operational use;
  human decision for every enforcement action; no automated fines.
