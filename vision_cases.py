"""Deterministic synthetic operations screenshots and a diagram; no real system data."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent / 'fixtures' / 'vision'
ROOT.mkdir(parents=True, exist_ok=True)
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
SANS = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
cases = []


def save(name, image, prompt, expected):
    path = ROOT / (name + '.png')
    image.save(path)
    cases.append({'id': name, 'image': 'fixtures/vision/' + path.name,
                  'image_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'prompt': prompt, 'expected': expected})


def terminal(name, lines, prompt, expected):
    image = Image.new('RGB', (1440, 720), '#15202b')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(MONO, 26)
    for i, line in enumerate(lines):
        draw.text((35, 35 + i * 48), line, fill='#ecf1f5', font=font)
    save(name, image, prompt, expected)


terminal('nginx-error', [
    '$ sudo nginx -t',
    'nginx: [emerg] unknown directive "prox_pass" in',
    '/etc/nginx/conf.d/api.conf:17',
    'nginx: configuration file /etc/nginx/nginx.conf test failed',
], 'Read this terminal screenshot. Return JSON only with the keys file, line, and directive '
   'for the reported configuration error.',
   {'file': '/etc/nginx/conf.d/api.conf', 'line': 17, 'directive': 'prox_pass'})

terminal('disk-usage', [
    '$ df -h',
    'Filesystem         Size  Used Avail Use% Mounted on',
    '/dev/nvme0n1p2     200G   62G  128G  33% /',
    '/dev/mapper/logs    40G   31G    7G  83% /var/log',
    '/dev/mapper/data     2T  1.8T  175G  91% /srv/data',
    'tmpfs              16G   32M   16G   1% /run',
], 'Which mounted filesystem has the highest reported Use%? Return JSON only with '
   'the keys mount and use_percent.', {'mount': '/srv/data', 'use_percent': 91})

terminal('service-ports', [
    '$ ss -lnt',
    'State   Recv-Q Send-Q Local Address:Port  Peer Address:Port',
    'LISTEN  0      128    127.0.0.1:5432      0.0.0.0:*',
    'LISTEN  0      511    0.0.0.0:443         0.0.0.0:*',
    'LISTEN  0      128    [::1]:5432          [::]:*',
    'LISTEN  0      128    0.0.0.0:22          0.0.0.0:*',
], 'Does the database port shown here listen on a non-loopback interface? Return '
   'JSON only with the key non_loopback and a boolean value.', {'non_loopback': False})

image = Image.new('RGB', (1200, 720), 'white')
draw = ImageDraw.Draw(image)
font = ImageFont.truetype(SANS, 35)
boxes = {'Browser': (35, 275, 275, 400), 'Edge': (425, 275, 665, 400),
         'API': (835, 130, 1110, 255), 'Database': (835, 480, 1110, 605)}
for label, rect in boxes.items():
    draw.rounded_rectangle(rect, radius=15, fill='#dce8f3', outline='#334e68', width=4)
    draw.text(((rect[0]+rect[2])/2, (rect[1]+rect[3])/2), label,
              fill='black', font=font, anchor='mm')
for points in [[(275, 337), (425, 337)], [(665, 337), (835, 192)], [(972, 255), (972, 480)]]:
    a, b = points
    draw.line(points, fill='black', width=6)
    import math
    angle = math.atan2(b[1]-a[1], b[0]-a[0])
    draw.polygon([b, (b[0]-24*math.cos(angle-.5), b[1]-24*math.sin(angle-.5)),
                       (b[0]-24*math.cos(angle+.5), b[1]-24*math.sin(angle+.5))], fill='black')
save('request-path', image,
     'Follow the directed arrows from Browser. Return JSON only with the key path and '
     'an ordered list of the node labels visited, including Browser.',
     {'path': ['Browser', 'Edge', 'API', 'Database']})

source = Path(__file__).parent / 'fixtures' / 'vision.png'
with Image.open(source) as original:
    save('printed-code', original,
         'Read the printed code and the colors of the left and right boxes. Return JSON only '
         'with keys code, left, and right.', {'code': 'ULMUS-731', 'left': 'red', 'right': 'blue'})

(ROOT / 'cases.jsonl').write_text('\n'.join(json.dumps(x) for x in cases) + '\n')
print('Created', len(cases), 'synthetic vision cases')
