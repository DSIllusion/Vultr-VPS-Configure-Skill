---
name: vultr-clash-recovery
description: Diagnose Mac Wi-Fi direct connectivity to a user's Vultr VPS and recover a self-hosted Clash Verge Rev subscription. Use when the VPS or subscription is unreachable, the user wants to evaluate replacement servers, or a new node needs deployment and Mac acceptance testing.
---

# Vultr and Clash recovery

Use the user's current budget, preferred regions, device networks, and backup preferences. Before relying on old addresses or credentials, identify the active instance and profile. The desired result is direct device-to-VPS connectivity and a consistent VPS egress for traffic routed through the node.

1. **Diagnose before replacing.** Check whether the failure is local connectivity, DNS, the VPS network path, the server listener, the proxy handshake, or the subscription endpoint. On macOS, bind direct checks to the actual Wi-Fi interface and bypass application proxy settings. Account for TUN capture and synthetic Clash DNS answers. Compare numeric TCP tests and a known-good control; use a real resolved address with TLS hostname validation for HTTPS. An unconfigured port or failed ping alone does not establish IP reachability or filtering. If the existing service works, keep it.
2. **Screen replacements without charges.** Compare published provider test endpoints from the actual networks available to you. Record the network, endpoint, protocol, and outcome. Treat these checks as regional screening only. A specific assigned IP is accepted based on tests of that IP.
3. **Provision a single approved candidate.** Verify region, current pricing and inventory, OS, public IPv4, optional fees, and SSH access. Show the exact resource and expected cost before a paid deployment and proceed with specific user authorization. Preserve a usable fallback unless the user explicitly authorizes deleting it. After an ambiguous submission, check the instance list before attempting another create. Never churn paid instances or addresses without an agreed retry budget. Confirm irreversible deletion for the particular resource and verify removal separately.
4. **Deploy and package.** Use [deployment and acceptance](references/deployment-and-acceptance.md) when creating or repairing the server or subscription. Verify SSH host identity, use authenticated access, and protect all secrets. Test the new node in isolation before switching the active Mac profile.
5. **Install and verify.** Import the private HTTPS subscription in Clash Verge Rev, select the intended profile and node, and confirm the actual connection chain and egress through Clash. Keep a backup profile for rollback. Report what was proven on Mac and which other networks or devices remain untested.
