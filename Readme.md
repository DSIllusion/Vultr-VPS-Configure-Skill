# Vultr VPS Configure Skill

`vultr-clash-recovery` is a Codex skill for troubleshooting a Vultr VPS connection from macOS and setting up or restoring a self-hosted Clash Verge Rev subscription.

## What it does

- Separates local network, DNS, server listener and proxy failures before recommending a replacement.
- Screens candidate regions, then tests the actual IP assigned to the selected instance. A provider speed-test endpoint is not proof that the assigned IP works.
- Validates the subscription, the connection through Clash and the actual egress IP. Keeps the previous working profile available for rollback.
- Restores Vultr account bandwidth reporting with a separate read-only key from the Mac login Keychain. If the user allows any IPv4 for this reader, recurring server replacement requires no IP allowlist changes.

## Install in Codex

Clone this repository and run these commands from the repository root on the Mac where Codex runs:

```bash
mkdir -p ~/.agents/skills
cp -R vultr-clash-recovery ~/.agents/skills/
```

Copy the whole skill directory, including `references/`. If the skill is already installed, compare the copies before replacing it.

## Use it

> Use $vultr-clash-recovery to diagnose why my Mac cannot reach my Vultr VPS. Start with read-only checks and report what you verified before proposing changes.

> Use $vultr-clash-recovery to configure the replacement VPS and restore monthly Vultr usage in Clash from my existing Mac login Keychain entry.

## Command-line workflow

Use Python 3 and Clash Verge Rev on the Mac. For API ordering, register the Mac's SSH public key in Vultr and save a separate management API key under the local login Keychain service `Codex.Vultr.Management`. Its service user needs `compute.instance.Create`, `compute.instance.List`, and `compute.instance.Read`. Store the bandwidth-only key under `Codex.Vultr.AccountBandwidth`. The management key stays on the Mac. Only the read-only key goes to the VPS.

```bash
python3 vultr-clash-recovery/scripts/vultr_clash.py --region icn --max-monthly 5 --quote-only

python3 vultr-clash-recovery/scripts/vultr_clash.py --region icn --max-monthly 5 \
  --order --confirm-create --order-label my-approved-order-01 \
  --management-account YOUR_KEYCHAIN_ACCOUNT --ssh-key-id YOUR_VULTR_SSH_KEY_UUID \
  --identity ~/.ssh/id_ed25519
```

The second command places a paid order. Reuse the same order label and local state directory if the request or first boot times out. For a VPS already provisioned with your SSH key, use `--fresh-ip` with its allocated IPv4. Both deployment modes remember the first SSH host key and refuse later key changes. Use them only after accepting this first-connection behavior. `--no-import` runs isolated checks without changing the active profile. For a normal deployment, select the imported subscription in Clash, then press Enter in the terminal to verify egress.

The helper does not destroy instances or change allowlists. If the service reader restricts IPv4 sources, add the new address in Vultr before deployment. If the local Keychain asks for access, approve it on your Mac. See `--help` for optional Wi-Fi-bound API connection settings.

API ordering, IP allocation, and SSH key login were tested on an actual instance. Read-only account usage was tested from a second source. The combined deployment command also has local checks for retries and subscription behavior. Its full sequence has not yet been tested on a second fresh paid instance.

Provisioning, deleting an instance, or changing network settings requires the appropriate user approval. Keep private keys, tokens and subscription URLs out of the repository and logs.

See [SKILL.md](vultr-clash-recovery/SKILL.md) and the [deployment and acceptance checklist](vultr-clash-recovery/references/deployment-and-acceptance.md).
