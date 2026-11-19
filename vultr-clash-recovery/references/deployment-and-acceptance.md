# Deployment and acceptance

## Secure access and host setup

- Use the approved instance's actual public IPv4. Confirm identity by comparing the SSH host key fingerprint with the provider console, then use strict host key checking. Prefer an authorized public key at provisioning. If bootstrap requires console login or verification, hand that step to the user. Do not print or transmit secrets in chat, command arguments, screenshots, or browser logs.
- Validate direct TCP and an actual SSH banner from Mac over the identified physical interface. Check that the server service is listening before interpreting failed connections to other ports. Prefer official packages or releases and verify the installed software version.
- For the existing pattern, deploy sing-box VLESS Reality with a fresh client ID and key material for the new instance. Validate the configuration before startup. Open the required TCP listener(s) in the host firewall and provider firewall as applicable. Keep access to the provider console while making network changes. Scope a root management key only to the intended host and keep local profiles and credentials private.

## Subscription

- Serve a Clash-compatible config over HTTPS with a valid certificate and a high-entropy private subscription path. Reuse the same published subscription only if it still belongs to the intended server and its secret is valid. If creating a replacement, give it a recognizable name. Keep the backend on loopback behind the HTTPS server. Avoid logging the token path and check certificates without disabling TLS verification.
- Verify the private URL returns HTTP 200, parses as Clash config, points to the correct instance, and has no stale upstream dependency for a direct setup. Check that anonymous requests fail. Store the subscription URL privately and share it through an agreed secure mechanism.
- Optional usage display: label local interface statistics as estimates. If the user wants Vultr account bandwidth, use a separate IAM service identity with only `account.bandwidth.Read`, a dedicated key, and a single-server IP allowlist. Store the key server-side, separate from the subscription URL and body. Use the current-month account bandwidth response and check the official units and credits fields. Test the bandwidth endpoint and confirm unrelated instance access is denied. Keep subscription delivery available if usage lookup fails by omitting stale or unavailable statistics, or using known-current cached values.

## Mac acceptance and rollback

- In an isolated temporary profile or client instance, use the new node for an HTTPS request and an IP echo request. Verify the end-to-end connection and expected public egress. When an existing TUN could provide a route, verify the test core uses the physical Wi-Fi path before calling it direct.
- In Clash Verge Rev, import the private HTTPS URL, refresh the subscription, and select the new profile and node. Verify a request through the actual Clash listener and an IP echo match. Confirm direct rules remain effective when the user requested split routing. Check usage display if configured. If switching breaks connectivity, restore the previous working profile and diagnose before retrying.
- Record the candidate region and IP, the cost shown in the console, tests and observed egress, any remaining unknowns, and the private handoff location. Tests on Mac do not certify mobile data, company Wi-Fi, other devices, or access to a particular service.
