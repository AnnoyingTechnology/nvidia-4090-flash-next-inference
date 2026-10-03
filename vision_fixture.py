"""Generate a deterministic grounding fixture; the request contains no answer hints."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

image = Image.new('RGB', (768, 512), 'white')
draw = ImageDraw.Draw(image)
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 64)
draw.text((150, 60), 'ULMUS-731', fill='black', font=font)
draw.rectangle((70, 230, 330, 450), fill='red')
draw.rectangle((440, 230, 700, 450), fill='blue')
out = Path(__file__).parent / 'fixtures' / 'vision.png'
out.parent.mkdir(exist_ok=True)
image.save(out)
print(out)
