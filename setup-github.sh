#!/usr/bin/env bash
# One-time setup: create the public repo, push it, load the OCI secrets, kick off a test run.
# Run once:  bash "/e/Antigravity New/oci-vm-hunter/setup-github.sh"
set -e

D="/e/Antigravity New/oci-vm-hunter"
KEY="/c/Users/arpit/Downloads/arpittyagiji6@gmail.com-2026-09-07T16_31_27.023Z.pem"

cd "$D"

echo ">> creating + pushing repo"
gh repo create oci-vm-hunter --public --source=. --remote=origin --push

echo ">> loading secrets"
gh secret set OCI_CLI_USER        --body "ocid1.user.oc1..aaaaaaaa5emrhgsf5smsti7if43c2d3eux4oglpe2wwujkiplscfyf7t6q7q"
gh secret set OCI_CLI_TENANCY     --body "ocid1.tenancy.oc1..aaaaaaaa3mtrn6tvsmwk77iimdn2ke2pslexvx6xbhj7vnjwtoxylqehvi5a"
gh secret set OCI_CLI_FINGERPRINT --body "58:ab:b7:c3:78:57:3e:2b:29:a4:40:a1:88:f7:49:9c"
gh secret set OCI_CLI_REGION      --body "ap-hyderabad-1"
sed '/^OCI_API_KEY$/d' "$KEY" | gh secret set OCI_CLI_KEY_CONTENT

echo ">> starting a test run"
gh workflow run hunt.yml
sleep 15
gh run list --workflow=hunt.yml --limit 3

echo
echo "Done. Live at: https://github.com/Aurixelgh/oci-vm-hunter/actions"
