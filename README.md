# oci-vm-hunter

Retries launching an Oracle Cloud **Always Free** ARM instance
(`VM.Standard.A1.Flex`) in Hyderabad every ~5 minutes until capacity is
granted, then stops on its own.

- Runs entirely on GitHub's servers — your laptop can be off.
- Tries **2 OCPU/12 GB → 1 OCPU/12 GB → 1 OCPU/6 GB**, across all 3 fault domains.
- `no capacity` = normal, the run stays green. When it lands it opens a GitHub
  **issue** (you get an email) and every later run becomes a no-op.

## Watch it
Repo → **Actions** tab → **hunt**.

## Stop it
Actions tab → **hunt** → **···** → **Disable workflow**.

## Credentials
Stored as encrypted repo **secrets** (`OCI_CLI_*`), never printed in logs, never
shared with forks. The OCIDs and SSH public key in `hunt.yml` are identifiers,
not secrets. To revoke access later: OCI console → your profile → Tokens and
keys → delete the API key.

## Notes
- GitHub disables scheduled workflows after **60 days** of no repo commits —
  push any small change to re-arm it.
- Scheduled runs can be delayed 5–15 min under GitHub load; that's fine here.
