---
name: vultr-clash-recovery
description: Diagnose Mac Wi-Fi direct connectivity to a user's Vultr VPS and recover a self-hosted Clash Verge Rev subscription. Use when the VPS or subscription is unreachable, the user wants to evaluate replacement servers, or a new node needs deployment and Mac acceptance testing.
---

# Vultr and Clash recovery

Use the user's current budget, preferred regions, device networks, and backup preferences. Before relying on old addresses or credentials, identify the active instance and profile. The desired result is direct device-to-VPS connectivity and a consistent VPS egress for traffic routed through the node.

## Start from a short request

- Treat `$vultr-clash-recovery 换 VPS` as a request for the full replacement workflow below. A request to check connectivity runs the diagnostic step only. If the user invokes the skill without saying what they want, ask whether to check the current VPS or replace it.
- For a replacement, use any budget the user already stated. If they omitted it, ask once: “预算照旧，按每月 5 美元上限吗？” Treat “照旧” as that limit for this setup. Begin the free Wi-Fi checks while waiting. Confirm the specific price and candidate before placing any paid order.
- For a short replacement request, test direct connectivity from the Mac's current Wi-Fi first. When replacement is needed, test the approved candidate's assigned IPv4, deploy the subscription, import it into Clash Verge Rev, and verify the Mac's egress after activation. If the current VPS passes the checks but the user explicitly wants to replace it anyway, report the result and continue with candidate selection. If Clash requires a manual activation click, ask at that point and resume verification afterward.

## Recovery workflow

1. **Diagnose before replacing.** Check whether the failure is local connectivity, DNS, the VPS network path, the server listener, the proxy handshake, or the subscription endpoint. On macOS, bind direct checks to the actual Wi-Fi interface and bypass application proxy settings. Account for TUN capture and synthetic Clash DNS answers. Compare numeric TCP tests and a known-good control; use a real resolved address with TLS hostname validation for HTTPS. An unconfigured port or failed ping alone does not establish IP reachability or filtering. If the existing service works and the user wants to restore connectivity, keep it.
2. **Screen replacements without charges.** Compare published provider test endpoints from the actual networks available to you. Record the network, endpoint, protocol, and outcome. Treat these checks as regional screening only. A specific assigned IP is accepted based on tests of that IP.
3. **Provision a single approved candidate.** Verify region, current pricing and inventory, OS, public IPv4, optional fees, and SSH access. Show the exact resource and expected cost before a paid deployment and proceed with specific user authorization. Prefer [the command-line helper](scripts/vultr_clash.py) when the Mac has a Vultr management key and a registered SSH public key. Keep the same unique order label after a timeout and reconcile the instance list before initiating another order. Preserve usable fallback access. Confirm irreversible deletion for the particular resource and verify removal separately.
4. **Deploy and package.** Use [deployment and acceptance](references/deployment-and-acceptance.md). Authenticate SSH and protect all secrets. If the user accepts trust on first use for a fresh IP returned by Vultr, record that host key with `accept-new` and stop on changes. Otherwise independently verify the host fingerprint before running the deployment. Restore account bandwidth using the separate read-only key in the Mac login Keychain. A service identity that permits the new IPv4 already needs no allowlist update. Test the new node in isolation before switching the active Mac profile.
5. **Install and verify.** Import the private HTTPS subscription in Clash Verge Rev, select the intended profile and node, and confirm the actual connection chain and egress through Clash. Keep a backup profile for rollback. Report what was proven on Mac and which other networks or devices remain untested.
