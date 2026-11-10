import sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
import pillow_heif; pillow_heif.register_heif_opener()
src, out, maxw = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 1400
im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
W,H = im.size; s = min(1, maxw/max(W,H)); im = im.resize((int(W*s), int(H*s)))
d = ImageDraw.Draw(im); f = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 16)
for p in range(0, 101, 5):
    x = int(im.width*p/100); y = int(im.height*p/100)
    c = (255,0,0) if p%10==0 else (255,160,0)
    d.line([(x,0),(x,im.height)], fill=c, width=1); d.line([(0,y),(im.width,y)], fill=c, width=1)
    if p%10==0: d.text((x+2,2), str(p), fill=(255,255,0), font=f); d.text((2,y+2), str(p), fill=(255,255,0), font=f)
im.save(out, quality=85); print(W,H)
