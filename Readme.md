# Vultr VPS Configure Skill

`vultr-clash-recovery` is a Codex skill for troubleshooting a Vultr VPS connection from macOS and setting up or restoring a self-hosted Clash Verge Rev subscription.

## What it does

- Separates local network, DNS, server listener and proxy failures before recommending a replacement.
- Screens candidate regions, then tests the actual IP assigned to the selected instance. A provider speed-test endpoint is not proof that the assigned IP works.
- Validates the subscription, the connection through Clash and the actual egress IP. Keeps the previous working profile available for rollback.

## Install in Codex

Clone this repository and run these commands from the repository root on the Mac where Codex runs:

```bash
mkdir -p ~/.agents/skills
cp -R vultr-clash-recovery ~/.agents/skills/
```

Copy the whole skill directory, including `references/`. If the skill is already installed, compare the copies before replacing it.

## Use it

> Use $vultr-clash-recovery to diagnose why my Mac cannot reach my Vultr VPS. Start with read-only checks and report what you verified before proposing changes.

Provisioning, deleting an instance, or changing network settings requires the appropriate user approval. Keep private keys, tokens and subscription URLs out of the repository and logs.

See [SKILL.md](vultr-clash-recovery/SKILL.md) and the [deployment and acceptance checklist](vultr-clash-recovery/references/deployment-and-acceptance.md).
