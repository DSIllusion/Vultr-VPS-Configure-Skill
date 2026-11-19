# Deployment and acceptance

## Secure access and host setup

- Use the approved instance's actual public IPv4. Confirm identity by comparing the SSH host key fingerprint with the provider console, then use strict host key checking. Prefer an authorized public key at provisioning. If bootstrap requires console login or verification, hand that step to the user. Do not print or transmit secrets in chat, command arguments, screenshots, or browser logs.
- Validate direct TCP and an actual SSH banner from Mac over the identified physical interface. Check that the server service is listening before interpreting failed connections to other ports. Prefer official packages or releases and verify the installed software version.
- For the existing pattern, deploy sing-box VLESS Reality with a fresh client ID and key material for the new instance. Validate the configuration before startup. Open the required TCP listener(s) in the host firewall and provider firewall as applicable. Keep access to the provider console while making network changes. Scope a root management key only to the intended host and keep local profiles and credentials private.

## Subscription

- Serve a Clash-compatible config over HTTPS with a valid certificate and a high-entropy private subscription path. Reuse the same published subscription only if it still belongs to the intended server and its secret is valid. If creating a replacement, give it a recognizable name. Keep the backend on loopback behind the HTTPS server. Avoid logging the token path and check certificates without disabling TLS verification.
- Verify the private URL returns HTTP 200, parses as Clash config, points to the correct instance, and has no stale upstream dependency for a direct setup. Check that anonymous requests fail. Store the subscription URL privately and share it through an agreed secure mechanism.

## Restore Vultr account bandwidth on replacement

1. Reuse the existing service identity with only `account.bandwidth.Read`. Verify the new server's public egress IPv4 and update that identity's API allowlist to the exact new `/32`. Remove the retired address once it is no longer needed. Keep any overlap during migration limited to verified servers that still need access. Preserve the applicable authorization boundaries for changing access.
2. Find the item with label `Vultr-Account-Bandwidth` and service `Codex.Vultr.AccountBandwidth` in the Mac's local **login** Keychain. Its account should match the intended Vultr service identity. Use `/usr/bin/security find-generic-password -s Codex.Vultr.AccountBandwidth -a <service-account> -w` with `"$HOME/Library/Keychains/login.keychain-db"` as the final argument. Capture stdout privately and check the exit status before sending the key to the verified VPS through SSH stdin. Validate the key before replacing any existing file on the server. Keep the value out of process arguments, logs, clipboard history, and plaintext backups.

3. Keep the resulting key file server-side, readable only by root and the subscription service, for example owner `root`, group the service account's group, and mode `0640` in a restricted directory. The subscription URL and body must contain no Vultr API credential. If Keychain access prompts or is locked, ask the user to approve or unlock it locally. If the record is absent or the key is rejected after checking the allowlist and permissions, request an authorized replacement key and back it up in Keychain. Routine migrations reuse the existing key without manual entry.
4. Read `GET /v2/account/bandwidth` and use `current_month_to_date` outbound usage and current account credits for `Subscription-Userinfo`. Confirm the bandwidth endpoint succeeds and unrelated instance access is denied. If usage lookup fails, still deliver the subscription while omitting the usage header or using a verified same-period cache. Label any deliberately used local interface statistics as VPS-only estimates.
5. Check the subscription response header, then refresh the active Clash profile and compare its usage and total against the Vultr account response, allowing for display rounding.

## Mac acceptance and rollback

- In an isolated temporary profile or client instance, use the new node for an HTTPS request and an IP echo request. Verify the end-to-end connection and expected public egress. When an existing TUN could provide a route, verify the test core uses the physical Wi-Fi path before calling it direct.
- In Clash Verge Rev, import the private HTTPS URL, refresh the subscription, and select the new profile and node. Verify a request through the actual Clash listener and an IP echo match. Confirm direct rules remain effective when the user requested split routing. Check usage display if configured. If switching breaks connectivity, restore the previous working profile and diagnose before retrying.
- Record the candidate region and IP, the cost shown in the console, tests and observed egress, any remaining unknowns, and the private handoff location. Tests on Mac do not certify mobile data, company Wi-Fi, other devices, or access to a particular service.
