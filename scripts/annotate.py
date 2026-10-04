#!/usr/bin/env python3
"""Draw red box(es) + optional label on a screenshot, in place.

  python scripts/annotate.py evidence/BUG-003_x.png 120 64 300 40 "padding 12px vs 16px"
  python scripts/annotate.py img.png 10 10 50 50 "" 200 200 80 30 "2nd box"
Boxes are x y w h [label], repeated. Add --out new.png to keep the original.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

args = sys.argv[1:]
out = None
if "--out" in args:
    i = args.index("--out"); out = args[i + 1]; del args[i:i + 2]
path, rest = args[0], args[1:]
img = Image.open(path).convert("RGB")
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
except OSError:
    font = ImageFont.load_default()
i = 0
while i + 3 < len(rest):
    x, y, w, h = map(int, rest[i:i + 4]); i += 4
    label = ""
    if i < len(rest) and not rest[i].lstrip("-").isdigit():
        label = rest[i]; i += 1
    d.rectangle([x, y, x + w, y + h], outline=(230, 0, 0), width=3)
    if label:
        tb = d.textbbox((0, 0), label, font=font)
        ty = y - (tb[3] + 8) if y > tb[3] + 10 else y + h + 4
        d.rectangle([x, ty, x + tb[2] + 8, ty + tb[3] + 6], fill=(230, 0, 0))
        d.text((x + 4, ty + 2), label, fill="white", font=font)
img.save(out or path)
print("annotated", out or path)
