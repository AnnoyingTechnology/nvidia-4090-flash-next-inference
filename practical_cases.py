"""Frozen executable DevOps/Python cases and operational decision canaries.

Independent public examples and hidden cases exercise behavior, not code spelling.
Generated programs are executed only by the existing isolated official LCB grader.
"""
import json
from pathlib import Path


def program(name, prompt, public, private, control):
    def cases(rows):
        return json.dumps([{'input': '\n'.join(json.dumps(arg) for arg in args),
                            'output': json.dumps(expected)} for args, expected in rows])
    return {'id': name, 'kind': 'code', 'prompt': prompt,
            'problem': {'public_test_cases': cases(public), 'private_test_cases': cases(private),
                        'metadata': json.dumps({'func_name': 'solve'})}, 'control': control}


CASES = [
    program('size-parser',
        'Implement solve(text), a configuration size parser returning an integer byte count, or None for invalid input. '
        'Allow outer whitespace and a nonnegative plain decimal number, followed by optional whitespace and one of '
        'B, KB, MB, GB, KiB, MiB, GiB (case-insensitive). No suffix means bytes. SI uses 1000 and IEC uses 1024. '
        'A decimal must have digits before its optional dot and digits after it. Reject signs, exponents, unknown units, '
        'non-string inputs and results that are not integral bytes. Use exact decimal arithmetic. '
        'Examples: "1.5 KiB" -> 1536; "0.1 B" -> None. Return complete Python code in a code block.',
        [(['1.5 KiB'], 1536), (['0.1 B'], None)],
        [(['2 MB'], 2000000), ([' 0.125 mib '], 131072), (['1024'], 1024), (['0'], 0),
         (['-1GB'], None), (['1e3'], None), (['1 TB'], None), (['.5KiB'], None),
         (['1.'], None), ([3], None), (['1.001 KB'], 1001), (['9007199254740993'], 9007199254740993)],
        'import re\nfrom decimal import Decimal\ndef solve(text):\n'
        ' if not isinstance(text,str): return None\n'
        ' m=re.fullmatch(r"\\s*([0-9]+(?:\\.[0-9]+)?)\\s*([a-zA-Z]*)\\s*",text)\n'
        ' if not m: return None\n'
        ' units={"":1,"b":1,"kb":1000,"mb":1000000,"gb":1000000000,"kib":1024,"mib":1048576,"gib":1073741824}\n'
        ' if m[2].lower() not in units: return None\n'
        ' n=Decimal(m[1])*units[m[2].lower()]\n return int(n) if n==n.to_integral_value() else None'),
    program('secret-redaction',
        'Implement solve(record), returning a recursively copied JSON-compatible value. In every dictionary, '
        'replace values of keys authorization, cookie, set-cookie, x-api-key, password, token and secret '
        '(case-insensitive exact key match) with "[REDACTED]", regardless of value type. '
        'Traverse dictionaries and lists; retain other keys and scalar values exactly. Do not mutate the input. '
        'Example: {"headers":{"Authorization":"Bearer abc"},"count":2} becomes '
        '{"headers":{"Authorization":"[REDACTED]"},"count":2}. Return complete Python code in a code block.',
        [([{'Authorization': 'abc', 'count': 2}], {'Authorization': '[REDACTED]', 'count': 2})],
        [([{'items': [{'Token': 'xyz'}, {'token_count': 7}]}], {'items': [{'Token': '[REDACTED]'}, {'token_count': 7}]}),
         ([{'Password': {'nested': 1}, 'secret': None}], {'Password': '[REDACTED]', 'secret': '[REDACTED]'}),
         ([['unchanged', 3, None, {'COOKIE': 'a=b'}]], ['unchanged', 3, None, {'COOKIE': '[REDACTED]'}]),
         ([{'a': {'b': {'x-API-key': '123'}}, 'authorization_mode': 'bearer'}],
          {'a': {'b': {'x-API-key': '[REDACTED]'}}, 'authorization_mode': 'bearer'})],
        'def solve(x):\n'
        ' if isinstance(x,dict): return {k:"[REDACTED]" if k.lower() in '
        '{"authorization","cookie","set-cookie","x-api-key","password","token","secret"} else solve(v) for k,v in x.items()}\n'
        ' if isinstance(x,list): return [solve(v) for v in x]\n return x'),
    program('deployment-reconcile',
        'Implement solve(current, desired), where both arguments map service names to JSON configuration values. '
        'Return a deterministic list of operations to make current exactly equal desired. For each service name '
        'in sorted order over the union of names: emit {"action":"remove","service":name} if absent from desired; '
        'emit {"action":"apply","service":name,"config":desired[name]} if new or if configuration differs by '
        'JSON structural equality. Otherwise emit nothing. Never mutate inputs. Lists are ordered; dictionary key '
        'order is irrelevant; empty and null values are legitimate. Examples: equal inputs -> []; '
        '{} and {"web":{"port":80}} -> [{"action":"apply","service":"web","config":{"port":80}}]. '
        'Return complete Python code in a code block.',
        [([{}, {'web': {'port': 80}}], [{'action': 'apply', 'service': 'web', 'config': {'port': 80}}])],
        [([{'web': {'port': 80}}, {'web': {'port': 80}}], []),
         ([{'old': {}, 'web': {'port': 80}}, {'web': {'port': 443}, 'db': None}],
          [{'action': 'apply', 'service': 'db', 'config': None}, {'action': 'remove', 'service': 'old'},
           {'action': 'apply', 'service': 'web', 'config': {'port': 443}}]),
         ([{'x': {'a': 1, 'b': 2}}, {'x': {'b': 2, 'a': 1}}], []),
         ([{'x': [1, 2]}, {'x': [2, 1]}], [{'action': 'apply', 'service': 'x', 'config': [2, 1]}]),
         ([{'x': None}, {'x': {}}], [{'action': 'apply', 'service': 'x', 'config': {}}]),
         ([{'z': 0, 'a': 1}, {}], [{'action': 'remove', 'service': 'a'}, {'action': 'remove', 'service': 'z'}])],
        'def solve(current,desired):\n out=[]\n for name in sorted(set(current)|set(desired)):\n'
        '  if name not in desired: out.append({"action":"remove","service":name})\n'
        '  elif name not in current or current[name]!=desired[name]: out.append({"action":"apply","service":name,"config":desired[name]})\n return out'),
    program('cidr-policy',
        'Implement solve(address, networks), returning whether an IPv4/IPv6 literal address belongs to any '
        'CIDR in the list. Use the Python standard library. IPv4-mapped IPv6 peers are normalized to IPv4. '
        'CIDRs may contain host bits (normalize with strict=False); malformed CIDRs are ignored. '
        'Malformed peer addresses, hostnames and addresses with a zone identifier return False. '
        'An empty list denies all. Version mismatches are ignored. Examples: "10.1.2.3", ["10.0.0.0/8"] -> True; '
        '"10.1.2.3", ["192.168.0.0/16"] -> False. Return complete Python code in a code block.',
        [(['10.1.2.3', ['10.0.0.0/8']], True), (['10.1.2.3', ['192.168.0.0/16']], False)],
        [(['::ffff:192.168.1.3', ['192.168.1.0/24']], True),
         (['2001:db8::123', ['2001:db8::/32']], True), (['10.0.0.7', ['bad', '10.0.0.1/24']], True),
         (['10.0.0.7', ['::/0']], False), (['localhost', ['0.0.0.0/0']], False),
         (['fe80::1%eth0', ['fe80::/10']], False), (['127.0.0.1', []], False),
         (['192.168.1.255', ['192.168.1.0/24']], True), (['192.168.2.0', ['192.168.1.0/24']], False)],
        'import ipaddress\ndef solve(address,networks):\n'
        ' if "%" in address: return False\n'
        ' try: peer=ipaddress.ip_address(address)\n except ValueError: return False\n'
        ' if isinstance(peer,ipaddress.IPv6Address) and peer.ipv4_mapped: peer=peer.ipv4_mapped\n'
        ' for value in networks:\n'
        '  try: net=ipaddress.ip_network(value,strict=False)\n'
        '  except ValueError: continue\n'
        '  if peer.version==net.version and peer in net: return True\n return False'),
]

# These decision cases intentionally offer explicit action choices. Their role is a bounded operational
# canary; they are not a replacement for evaluating complete real-world administration sessions.
for name, question, options, answer in [
    ('systemd-online', 'A service needs a configured network before startup. Which unit directives express '
     'ordering and activation of the online target?', ['After=network-online.target with Wants=network-online.target',
     'Before=network-online.target only', 'After=network.target only', 'Restart=always only'], 'A'),
    ('nginx-atomic', 'A candidate nginx configuration has been prepared. Which sequence minimizes risk '
     'before replacing it in service?', ['Restart first, then test syntax',
     'Validate candidate syntax, activate atomically, reload, verify health, retain rollback',
     'Disable the firewall, restart, then inspect logs', 'Delete the current config before creating the candidate'], 'B'),
    ('disk-deleted', 'df shows a full filesystem; du accounts for much less. A large deleted logfile is still '
     'held open by a process. What releases that allocation?', ['Run sync repeatedly', 'Delete more directory entries for that file',
     'Make the owning process close/reopen the descriptor through its supported rotation path', 'Drop page cache'], 'C'),
    ('ansible-idempotent', 'An Ansible task must create a directory with a known owner and mode. Which approach '
     'reports change only when the desired state differs?', ['shell: mkdir -p with changed_when: true',
     'command: mkdir on every run', 'Ignore all errors', 'ansible.builtin.file with state: directory, owner and mode'], 'D'),
    ('tls-sni', 'An HTTPS backend works by hostname, but connecting to its IP returns the wrong certificate. '
     'Which diagnostic preserves SNI and the Host header?', ['curl --resolve hostname:443:IP https://hostname/',
     'curl -k https://IP/ as the final fix', 'Disable certificate verification globally', 'Replace all certificates'], 'A'),
    ('postgres-rollback', 'A database migration drops a column needed by the currently deployed application. '
     'A fast application rollback must remain possible. Which rollout supports this?',
     ['Drop first, deploy later', 'Expand/contract: preserve old schema through the rollback window',
      'Delete the backup after migration', 'Disable all application checks'], 'B'),
    ('dns-authority', 'A recursive resolver returns a stale answer while the authoritative nameserver returns '
     'the new one. Which explanation fits?', ['TLS certificate expiration', 'The hostname is permanently invalid',
     'A cached record remains valid until its TTL expires', 'HTTP keepalive determines authoritative DNS'], 'C'),
    ('ssh-locked-out', 'A remote SSH configuration change could remove access. Which validation sequence is safest?',
     ['Close the working connection and restart immediately', 'Disable authentication to test connectivity',
      'Delete authorized_keys first', 'Keep the current session, validate sshd configuration, reload, test a second session'], 'D'),
]:
    CASES.append({'id': name, 'kind': 'decision', 'prompt': question + '\n' +
                  '\n'.join(f'{chr(65+i)}. {text}' for i, text in enumerate(options)) +
                  '\nReturn only the correct letter.', 'answer': answer})


if __name__ == '__main__':
    path = Path(__file__).parent / 'eval/practical-cases.jsonl'
    path.write_text(''.join(json.dumps(row) + '\n' for row in CASES))
    print(path)
