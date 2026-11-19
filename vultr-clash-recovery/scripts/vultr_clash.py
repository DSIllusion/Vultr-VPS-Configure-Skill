#!/usr/bin/env python3
"""Quote a Vultr instance, or configure a newly created Ubuntu 24.04 VPS."""

import argparse
import concurrent.futures
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import uuid


PLAN = 'vc2-1c-1gb'
KEYCHAIN_SERVICE = 'Codex.Vultr.AccountBandwidth'
MANAGEMENT_SERVICE = 'Codex.Vultr.Management'
API_ROUTE = []

SUBSCRIPTION = r'''
import hmac, json, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

root = Path('/var/lib/vultr-clash-subscription')
token = (root / 'token').read_text().strip()
body = (root / 'profile.json').read_bytes()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if not hmac.compare_digest(self.path.encode(), ('/' + token).encode()):
            self.send_error(404)
            return
        usage = None
        try:
            key = (root / 'bandwidth-key').read_text().strip()
            req = urllib.request.Request(
                'https://api.vultr.com/v2/account/bandwidth',
                headers={'Authorization': 'Bearer ' + key})
            with urllib.request.urlopen(req, timeout=5) as response:
                month = json.load(response)['bandwidth']['current_month_to_date']
            used = int(month['gb_out']) * 1024**3
            total = sum(int(month[k]) for k in ('free_bandwidth_credits',
                        'instance_bandwidth_credits', 'purchased_bandwidth_credits')) * 1024**3
            if used >= 0 and total > 0:
                usage = f'upload=0; download={used}; total={total}; expire=0'
        except (OSError, ValueError, TypeError, KeyError):
            pass
        self.send_response(200)
        self.send_header('Content-Type', 'application/yaml; charset=utf-8')
        self.send_header('Content-Disposition', 'attachment; filename="vultr-vps.yaml"')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        if usage is not None:
            self.send_header('Subscription-Userinfo', usage)
        self.end_headers()
        self.wfile.write(body)

ThreadingHTTPServer(('127.0.0.1', 18765), Handler).serve_forever()
'''

REMOTE = r"""
import fcntl, grp, json, os, pathlib, secrets, subprocess, sys, uuid

settings = json.load(sys.stdin)
root = pathlib.Path('/var/lib/vultr-clash-subscription')
marker = pathlib.Path('/root/.vultr-clash-managed')
sing = pathlib.Path('/etc/sing-box/config.json')
caddy = pathlib.Path('/etc/caddy/Caddyfile')

def run(*args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if result.returncode:
        raise SystemExit('Failed: ' + ' '.join(args[:2]))
    return result.stdout

def write(path, data, mode, group=0):
    temp = path.with_name(path.name + '.new')
    try:
        with os.fdopen(os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode), 'w') as out:
            out.write(data)
        os.chown(temp, 0, group)
        os.chmod(temp, mode)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)

os.umask(0o077)
lock = open('/run/lock/vultr-clash-deploy.lock', 'a')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit('Another deployment is already running') from None
if 'VERSION_ID="24.04"' not in pathlib.Path('/etc/os-release').read_text():
    raise SystemExit('Expected Ubuntu 24.04')
if not marker.exists():
    if any(p.exists() for p in (sing, caddy, root)):
        raise SystemExit('Existing services detected; use a fresh instance')
    write(marker, settings['ip'], 0o600)
elif marker.read_text() != settings['ip']:
    raise SystemExit('Instance IP differs from deployment marker')

os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
source = pathlib.Path('/etc/apt/sources.list.d/vultr-clash-sagernet.sources')
if not source.exists():
    run('apt-get', 'update', '-qq')
    run('apt-get', 'install', '-y', '-qq', 'ca-certificates', 'curl')
    pathlib.Path('/etc/apt/keyrings').mkdir(exist_ok=True)
    public_key = pathlib.Path('/etc/apt/keyrings/vultr-clash-sagernet.asc')
    key_data = run('curl', '-fsSL', 'https://sing-box.app/gpg.key').decode()
    write(public_key, key_data, 0o644)
    write(source, 'Types: deb\nURIs: https://deb.sagernet.org/\nSuites: *\n'
                  'Components: *\nSigned-By: /etc/apt/keyrings/vultr-clash-sagernet.asc\n', 0o644)
run('apt-get', 'update', '-qq')
run('apt-get', 'install', '-y', '-qq', 'sing-box', 'caddy', 'ufw')
if subprocess.run(['id', 'vultr-clash-sub'], stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL).returncode:
    run('useradd', '--system', '--no-create-home', '--shell', '/usr/sbin/nologin', 'vultr-clash-sub')
gid = grp.getgrnam('vultr-clash-sub').gr_gid
root.mkdir(mode=0o750, exist_ok=True)
os.chown(root, 0, gid)
profile_path = root / 'profile.json'
token_path = root / 'token'
name = settings['name']
ip = settings['ip']
domain = ip.replace('.', '-') + '.sslip.io'
if not profile_path.exists():
    pairs = dict(line.split(': ', 1) for line in
                 run('sing-box', 'generate', 'reality-keypair').decode().splitlines() if ': ' in line)
    uid = str(uuid.uuid4())
    short = secrets.token_hex(4)
    sni = 'www.microsoft.com'
    config = {'log': {'level': 'warn'}, 'inbounds': [{
        'type': 'vless', 'listen': '0.0.0.0', 'listen_port': 443,
        'users': [{'uuid': uid, 'flow': 'xtls-rprx-vision'}],
        'tls': {'enabled': True, 'server_name': sni, 'reality': {
            'enabled': True, 'handshake': {'server': sni, 'server_port': 443},
            'private_key': pairs['PrivateKey'], 'short_id': [short]}}}],
        'outbounds': [{'type': 'direct', 'tag': 'direct'}]}
    candidate = sing.with_name('config-check.json.tmp')
    write(candidate, json.dumps(config), 0o640, grp.getgrnam('sing-box').gr_gid)
    try:
        run('sing-box', 'check', '-c', str(candidate))
        candidate.replace(sing)
    finally:
        candidate.unlink(missing_ok=True)
    node = {'name': name, 'type': 'vless', 'server': ip, 'port': 443, 'uuid': uid,
            'udp': True, 'flow': 'xtls-rprx-vision', 'tls': True, 'servername': sni,
            'client-fingerprint': 'chrome',
            'reality-opts': {'public-key': pairs['PublicKey'], 'short-id': short}}
    profile = {'mode': 'rule', 'allow-lan': False, 'proxies': [node],
               'proxy-groups': [{'name': '代理', 'type': 'select', 'proxies': [name]}],
               'rules': ['GEOIP,CN,DIRECT', 'MATCH,代理']}
    write(profile_path, json.dumps(profile, ensure_ascii=False), 0o640, gid)
existing = json.loads(profile_path.read_text())['proxies'][0]
if existing['server'] != ip or existing['name'] != name:
    raise SystemExit('Existing managed profile differs; reuse the original name and IP')
if not token_path.exists():
    write(token_path, secrets.token_hex(32), 0o640, gid)

key = settings.get('bandwidth_key')
if key:
    import urllib.error
    import urllib.request
    req = urllib.request.Request('https://api.vultr.com/v2/account/bandwidth',
                                 headers={'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            json.load(response)['bandwidth']['current_month_to_date']['gb_out']
    except (OSError, ValueError, TypeError, KeyError):
        print('Bandwidth API unavailable; check the service account IP allowlist', file=sys.stderr)
    else:
        write(root / 'bandwidth-key', key + '\n', 0o640, gid)
write(pathlib.Path('/usr/local/bin/vultr-clash-subscription'),
      settings['subscription_source'], 0o755)
write(pathlib.Path('/etc/systemd/system/vultr-clash-subscription.service'), '''[Unit]
Description=Private Clash subscription
After=network-online.target
[Service]
User=vultr-clash-sub
Group=vultr-clash-sub
ExecStart=/usr/bin/python3 /usr/local/bin/vultr-clash-subscription
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
[Install]
WantedBy=multi-user.target
''', 0o644)
caddy_config = ('{\n    auto_https disable_redirects\n}\n'
                f'https://{domain}:8443 {{\n'
                '    tls {\n        issuer acme {\n            disable_tlsalpn_challenge\n'
                '        }\n    }\n    reverse_proxy 127.0.0.1:18765\n}\n')
candidate = caddy.with_name('Caddyfile.check')
write(candidate, caddy_config, 0o644)
try:
    run('caddy', 'validate', '--adapter', 'caddyfile', '--config', str(candidate))
    candidate.replace(caddy)
finally:
    candidate.unlink(missing_ok=True)
for port in (443, 80, 8443):
    run('ufw', 'allow', f'{port}/tcp')
run('systemctl', 'daemon-reload')
run('systemctl', 'enable', '--now', 'sing-box', 'caddy', 'vultr-clash-subscription')
run('systemctl', 'restart', 'sing-box', 'vultr-clash-subscription')
run('systemctl', 'reload', 'caddy')
run('systemctl', 'is-active', 'sing-box', 'caddy', 'vultr-clash-subscription')
print(f'https://{domain}:8443/' + token_path.read_text().strip())
"""

SWIFT_IMPORT = r'''
import AppKit
import Foundation
let value = String(decoding: FileHandle.standardInput.readDataToEndOfFile(), as: UTF8.self)
var url = URLComponents()
url.scheme = "clash"
url.host = "install-config"
guard let encoded = value.addingPercentEncoding(withAllowedCharacters: .alphanumerics) else { exit(1) }
url.percentEncodedQuery = "url=" + encoded
guard let final = url.url, NSWorkspace.shared.open(final) else { exit(1) }
'''


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(path, *, key=None, method='GET', payload=None):
    if API_ROUTE:
        return bound_api(path, key=key, method=method, payload=payload)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    headers = {'Accept': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    body = None
    if payload is not None:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(payload).encode()
    request = urllib.request.Request('https://api.vultr.com/v2/' + path, data=body,
                                     headers=headers, method=method)
    try:
        with opener.open(request, timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise SystemExit(f'Vultr API {method} {path.split("?")[0]}: HTTP {exc.code}') from None


def bound_api(path, *, key, method, payload):
    # curl reads the bearer header and JSON body from stdin, not its process arguments.
    options = ['url = ' + json.dumps('https://api.vultr.com/v2/' + path),
               'header = "Accept: application/json"']
    if key:
        options.append('header = ' + json.dumps('Authorization: Bearer ' + key))
    if payload is not None:
        options += ['header = "Content-Type: application/json"',
                    'data = ' + json.dumps(json.dumps(payload))]
    result = subprocess.run(['curl', '--silent', '--noproxy', '*', '--connect-timeout', '7',
                             '--max-time', '17', '--request', method,
                             '--write-out', '\n%{http_code}', *API_ROUTE, '--config', '-'],
                            input='\n'.join(options) + '\n', capture_output=True,
                            text=True, timeout=20)
    if result.returncode:
        raise SystemExit(f'Vultr API {method} transport failed (curl {result.returncode})')
    body, _, status = result.stdout.rpartition('\n')
    if not status.isdigit() or not (200 <= int(status) < 300):
        raise SystemExit(f'Vultr API {method} {path.split("?")[0]}: HTTP {status}')
    return json.loads(body) if body else {}


def listed(path, field, key=None):
    cursor = None
    seen = set()
    while True:
        query = {'per_page': 100}
        if cursor:
            query['cursor'] = cursor
        d = api(path + '?' + urllib.parse.urlencode(query), key=key)
        yield from d[field]
        cursor = d.get('meta', {}).get('links', {}).get('next')
        if not cursor:
            return
        if cursor in seen:
            raise SystemExit('Vultr pagination did not advance')
        seen.add(cursor)


def private_dir(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise SystemExit('State directory must be private to the current user')
    return path


def order_instance(args, key, base):
    name = args.order_label
    journal = private_dir(base / 'orders') / (name + '.json')
    if journal.exists():
        matches = [i for i in listed('instances', 'instances', key) if i.get('label') == name]
        if len(matches) != 1:
            raise SystemExit('Previous submission recorded; reconcile the Vultr instance list before placing another order')
        instance = matches[0]
        if instance.get('region') != args.region or instance.get('plan') != PLAN:
            raise SystemExit('Recorded order does not match the instance in Vultr')
    else:
        if any(i.get('label') == name for i in listed('instances', 'instances', key)):
            raise SystemExit('Order label already exists; choose a unique label for your approved order')
        if not quote(args.region, args.max_monthly):
            raise SystemExit('Approved plan is unavailable in this region')
        oses = [x['id'] for x in listed('os', 'os') if x.get('name') == 'Ubuntu 24.04 LTS x64']
        if len(oses) != 1:
            raise SystemExit('Could not uniquely identify Ubuntu 24.04 LTS x64')
        order = {'region': args.region, 'plan': PLAN, 'os_id': oses[0], 'label': name,
                 'backups': 'disabled', 'ddos_protection': False, 'enable_ipv6': False,
                 'disable_ipv4': False, 'sshkey_id': [args.ssh_key_id]}
        # Reserve the label before the only POST. A timeout never triggers a second order.
        with journal.open('x') as f:
            json.dump(order, f)
            f.flush()
            os.fsync(f.fileno())
        instance = api('instances', key=key, method='POST', payload=order)['instance']
    instance_id = str(uuid.UUID(instance['id']))
    print('Vultr instance:', instance_id, flush=True)
    for _ in range(36):
        i = api(f'instances/{instance_id}', key=key)['instance']
        try:
            addr = ipaddress.IPv4Address(i.get('main_ip') or '0.0.0.0')
        except ValueError:
            addr = None
        if addr is not None and addr.is_global and i.get('status') == 'active' and i.get('server_status') == 'ok':
            return str(addr)
        time.sleep(5)
    raise SystemExit('Instance is not ready yet; rerun with the same order label to resume polling')


def quote(region, budget):
    with concurrent.futures.ThreadPoolExecutor() as pool:
        plans = pool.submit(api, 'plans?type=vc2')
        inventory = pool.submit(api, f'regions/{region}/availability')
        plan = next(p for p in plans.result()['plans'] if p['id'] == PLAN)
        availability = inventory.result()['available_plans']
    location = plan.get('location_cost', {}).get(region, {})
    price = float(location.get('monthly_cost', plan['monthly_cost']))
    print(f'Vultr {region.upper()} · {PLAN} · USD {price:g}/month · '
          f'{"available" if PLAN in availability else "no current stock"}', flush=True)
    if price > budget:
        raise SystemExit('Listed plan exceeds the monthly budget')
    return PLAN in availability


def ssh_banner(ip, iface):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(7)
        # Darwin IP_BOUND_IF avoids testing a loopback/TUN proxy path.
        sock.setsockopt(socket.IPPROTO_IP, 25, socket.if_nametoindex(iface))
        sock.connect((ip, 22))
        if not sock.recv(240).startswith(b'SSH-2.0-'):
            raise SystemExit('No SSH banner from the new IP')


def wait_for_order_ssh(ip, iface):
    for attempt in range(6):
        try:
            ssh_banner(ip, iface)
            return
        except (OSError, SystemExit):
            if attempt == 5:
                raise SystemExit(
                    'The allocated instance is still present. SSH did not respond; '
                    'retry with the same order label instead of placing another order.'
                ) from None
            time.sleep(4)


def keychain(account, service=KEYCHAIN_SERVICE):
    args = ['/usr/bin/security', 'find-generic-password', '-s', service]
    if account:
        args += ['-a', account]
    p = subprocess.run(args + ['-w', str(Path.home() / 'Library/Keychains/login.keychain-db')],
                       capture_output=True, text=True, timeout=25)
    key = p.stdout.strip()
    if p.returncode or not re.fullmatch(r'[A-Za-z0-9_.~+/-]{16,512}={0,2}', key):
        return None
    return key


def subscription_check(url, ip, iface):
    host = urllib.parse.urlsplit(url).hostname
    args = ['curl', '--interface', iface, '--noproxy', '*', '--resolve',
            f'{host}:8443:{ip}', '--connect-timeout', '5', '--max-time', '12', '-s', '-D', '-']
    for attempt in range(8):
        p = subprocess.run(args + ['--config', '-'], input=f'url = "{url}"\n',
                           capture_output=True, text=True, timeout=15)
        headers, _, body = p.stdout.partition('\n\n')
        if p.returncode == 0 and re.match(r'^HTTP/\S+ 200\b', headers):
            profile = json.loads(body)
            node = profile['proxies'][0]
            if node['server'] != ip or 'dialer-proxy' in node:
                raise SystemExit('Subscription target or route is incorrect')
            public = subprocess.run(args + ['-o', '/dev/null', '-w', '%{http_code}',
                                            f'https://{host}:8443/'],
                                    capture_output=True, text=True, timeout=15, check=True)
            if public.stdout.strip().splitlines()[-1:] != ['404']:
                raise SystemExit('Unexpected response for unauthenticated subscription')
            return node, 'subscription-userinfo:' in headers.lower()
        time.sleep(min(attempt + 1, 4))
    raise SystemExit('Private HTTPS subscription did not become ready; retry with the same state directory')


def proxy_test(port, expected_ip):
    command = ['curl', '-fsS', '--socks5-hostname', f'127.0.0.1:{port}', '--noproxy', '', '--max-time', '12']
    result = subprocess.run(command + ['https://api.ipify.org'], capture_output=True, text=True)
    if result.returncode or result.stdout.strip() != expected_ip:
        return False
    google = subprocess.run(command + ['-o', '/dev/null', '-w', '%{http_code}',
                                      'https://www.google.com/generate_204'], capture_output=True, text=True)
    return google.returncode == 0 and google.stdout.strip() == '204'


def isolated_test(node, ip, iface, state):
    import tempfile
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    profile = {'mixed-port': port, 'bind-address': '127.0.0.1', 'allow-lan': False,
               'mode': 'rule', 'interface-name': iface, 'proxies': [node],
               'rules': ['MATCH,' + node['name']]}
    with tempfile.TemporaryDirectory(dir=state) as directory:
        path = Path(directory) / 'test.json'
        path.write_text(json.dumps(profile))
        core = subprocess.Popen(['/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo',
                                 '-d', directory, '-f', str(path)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(30):
                if core.poll() is not None:
                    raise SystemExit('Isolated Mihomo failed to start')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.2):
                        break
                except OSError:
                    time.sleep(.2)
            if not proxy_test(port, ip):
                raise SystemExit('Isolated proxy test failed; existing Clash selection kept')
        finally:
            if core.poll() is None:
                core.terminate()
                try:
                    core.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    core.kill()
                    core.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', required=True, help='Vultr region code, e.g. icn')
    parser.add_argument('--max-monthly', type=float, default=5)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--quote-only', action='store_true')
    modes.add_argument('--check-ip', help='Read-only Wi-Fi SSH probe')
    modes.add_argument('--fresh-ip', help='Public IP returned by your authorized Vultr order')
    modes.add_argument('--order', action='store_true', help='Place or resume one authorized paid Vultr order')
    modes.add_argument('--verify-ip', help='Verify the active Clash proxy without changing it')
    parser.add_argument('--identity', type=Path)
    parser.add_argument('--state-dir', type=Path, default=Path('./.vultr-clash'))
    parser.add_argument('--name')
    parser.add_argument('--interface', default='en0')
    parser.add_argument('--clash-port', type=int, default=7897)
    parser.add_argument('--keychain-account', help='Select an explicit account if the bandwidth service has multiple Keychain items')
    parser.add_argument('--skip-account-usage', action='store_true')
    parser.add_argument('--confirm-create', action='store_true', help='Confirm the paid order at the indicated budget')
    parser.add_argument('--order-label', help='Unique Vultr label. Keep it on retries to avoid duplicate charges')
    parser.add_argument('--ssh-key-id', help='UUID of the SSH public key registered in Vultr')
    parser.add_argument('--management-account', help='Mac Keychain account for the separate Vultr management key')
    parser.add_argument('--order-only', action='store_true', help='Verify ordering and IP without deployment')
    parser.add_argument('--no-import', action='store_true', help='Test the isolated node without changing Clash')
    parser.add_argument('--api-wifi', action='store_true', help='Bind API requests to the selected Mac interface')
    parser.add_argument('--api-doh', help='HTTPS resolver URL for API requests when macOS uses fake DNS addresses')
    parser.add_argument('--api-doh-resolve', help='Optional host:443:IPv4 mapping for the HTTPS resolver')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z]{3}', args.region) or not (0 < args.max_monthly < float('inf')):
        parser.error('Expected a three-letter region and positive finite monthly budget')
    if args.order_only and not args.order:
        parser.error('--order-only requires --order')
    if args.order and sys.platform != 'darwin':
        parser.error('Vultr management Keychain and Wi-Fi checks require macOS')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.interface):
        parser.error('Invalid network interface')
    if (args.api_doh or args.api_doh_resolve) and not args.api_wifi:
        parser.error('--api-doh and --api-doh-resolve require --api-wifi')
    if args.api_doh_resolve and not args.api_doh:
        parser.error('--api-doh-resolve requires --api-doh')
    if args.api_wifi:
        API_ROUTE.extend(['-4', '--interface', args.interface])
        if args.api_doh:
            if urllib.parse.urlsplit(args.api_doh).scheme != 'https':
                parser.error('--api-doh is an HTTPS URL')
            API_ROUTE.extend(['--doh-url', args.api_doh])
        if args.api_doh_resolve:
            API_ROUTE.extend(['--resolve', args.api_doh_resolve])
    if args.quote_only:
        return 0 if quote(args.region, args.max_monthly) else 1
    os.umask(0o077)
    if args.order:
        if not args.confirm_create or not args.management_account or not args.ssh_key_id:
            parser.error('--order requires --confirm-create, --management-account and --ssh-key-id')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{3,59}', args.order_label or ''):
            parser.error('--order requires a unique --order-label')
        args.ssh_key_id = str(uuid.UUID(args.ssh_key_id))
        if not args.order_only and (args.identity is None or not args.identity.expanduser().is_file()):
            parser.error('--order requires a readable --identity unless using --order-only')
        management_key = keychain(args.management_account, MANAGEMENT_SERVICE)
        if not management_key:
            raise SystemExit('Vultr management key not found in the Mac login Keychain')
        ip = order_instance(args, management_key, args.state_dir.resolve())
        print('Vultr assigned IP:', ip, flush=True)
    else:
        ip = str(ipaddress.IPv4Address(args.check_ip or args.fresh_ip or args.verify_ip))
    if not ipaddress.IPv4Address(ip).is_global:
        parser.error('Expected a public IPv4 address')
    if args.verify_ip:
        if not proxy_test(args.clash_port, ip):
            raise SystemExit('Active Clash proxy did not produce the expected egress and HTTPS result')
        print('Clash proxy verified:', ip)
        return 0
    if sys.platform != 'darwin':
        parser.error('Wi-Fi-bound checks require macOS')
    if args.order:
        wait_for_order_ssh(ip, args.interface)
    else:
        ssh_banner(ip, args.interface)
    print('Wi-Fi SSH banner received:', ip, flush=True)
    if args.check_ip:
        return 0
    if args.order_only:
        return 0
    if args.identity is None or not args.identity.expanduser().is_file():
        parser.error('--identity must name the SSH private key registered at provisioning')
    # The instance is already allocated, so current stock can differ.
    if not args.order:
        quote(args.region, args.max_monthly)
    name = args.name or f'Vultr {args.region.upper()} {ip}'
    if not name.strip() or any(c in name for c in ',\r\n'):
        parser.error('Invalid Clash node name')
    state = private_dir(args.state_dir.resolve() / ip)
    key = None if args.skip_account_usage else keychain(args.keychain_account)
    if not args.skip_account_usage and not key:
        print('Bandwidth Keychain item unavailable; proceeding without account usage.', file=sys.stderr)
    args_ssh = ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=accept-new', '-o', f'UserKnownHostsFile={state / "known_hosts"}',
                '-o', 'IdentitiesOnly=yes', '-o', f'ProxyCommand=nc -b {args.interface} -G 7 %h %p',
                '-i', str(args.identity.expanduser()), f'root@{ip}']
    import base64
    code = base64.b64encode(REMOTE.encode()).decode()
    command = f"python3 -c 'import base64;exec(base64.b64decode(\"{code}\"))'"
    payload = json.dumps({'ip': ip, 'name': name, 'bandwidth_key': key,
                          'subscription_source': SUBSCRIPTION})
    result = subprocess.run(args_ssh + [command], input=payload,
                            text=True, capture_output=True, timeout=480)
    if result.returncode:
        # Suppress untrusted diagnostics that might contain provisioning data.
        safe_prefixes = ('Failed: apt-get ', 'Failed: systemctl ', 'Failed: caddy ',
                         'Failed: sing-box ', 'Expected Ubuntu 24.04',
                         'Existing services detected;', 'Existing managed profile differs;',
                         'Another deployment is already running')
        reason = next((line for line in result.stderr.splitlines()
                       if line.startswith(safe_prefixes)), 'check SSH access and instance state')
        print('SSH deployment failed:', reason, file=sys.stderr)
        return 1
    url = result.stdout.strip()
    domain = ip.replace('.', '-') + '.sslip.io'
    if not re.fullmatch(r'https://' + re.escape(domain) + r':8443/[0-9a-f]{64}', url):
        raise SystemExit('Invalid deployment result')
    url_path = state / 'subscription-url.txt'
    fd = os.open(url_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        os.fchmod(out.fileno(), 0o600)
        out.write(url + '\n')
    print('Private subscription saved:', url_path, flush=True)
    node, has_usage = subscription_check(url, ip, args.interface)
    print('Subscription TLS verified; account usage:', 'available' if has_usage else 'unavailable', flush=True)
    isolated_test(node, ip, args.interface, state)
    print('Isolated proxy verified:', ip, flush=True)
    if args.no_import:
        return 0
    launched = subprocess.run(['/usr/bin/xcrun', 'swift', '-module-cache-path',
                               str(state / 'swift-cache'), '-e', SWIFT_IMPORT],
                              input=url, capture_output=True, text=True, timeout=90)
    if launched.returncode:
        raise SystemExit('Clash import could not be launched; the private subscription file is ready')
    if not sys.stdin.isatty():
        raise SystemExit('Clash import launched; activate the new profile and run --verify-ip from a terminal')
    input('Select the new Vultr subscription in Clash Verge, then press Enter here: ')
    if not proxy_test(args.clash_port, ip):
        raise SystemExit('Active Clash proxy did not pass verification')
    print('Clash proxy verified:', ip)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, StopIteration) as exc:
        raise SystemExit(f'Operation failed: {type(exc).__name__}. See the last completed step.') from None
