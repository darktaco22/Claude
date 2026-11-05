"""Builds the still images the Blender edit uses: a phone frame and the blurred key-art backdrop."""
import sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

out = sys.argv[1]; assets = sys.argv[2]
os.makedirs(out, exist_ok=True)
W, H = 1280, 720

# phone: screen 360x640 (the portrait capture at 2/3), bezel around it, transparent screen
sw, sh, b = 360, 640, 14
pw, ph = sw + 2 * b, sh + 2 * b
ph_img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
d = ImageDraw.Draw(ph_img)
d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=46, fill=(18, 12, 34, 255), outline=(255, 197, 46, 255), width=4)
d.rounded_rectangle([b, b, b + sw - 1, b + sh - 1], radius=30, fill=(0, 0, 0, 0))
d.rounded_rectangle([pw // 2 - 50, b + 8, pw // 2 + 50, b + 26], radius=9, fill=(10, 6, 20, 255))   # the notch
ph_img.save(os.path.join(out, "phone_frame.png"))
# a mask with the screen's rounded corners, for the footage
m = Image.new("L", (sw, sh), 0)
ImageDraw.Draw(m).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=30, fill=255)
m.save(os.path.join(out, "phone_mask.png"))

# backdrop: the game's key art, blurred and pushed to purple
art = Image.open(os.path.join(assets, "bg_title_wide.jpg")).convert("RGB")
a_w, a_h = art.size
crop_h = int(a_w * H / W)
art = art.crop((0, (a_h - crop_h) // 2, a_w, (a_h - crop_h) // 2 + crop_h)).resize((W, H), Image.LANCZOS)
blur = art.filter(ImageFilter.GaussianBlur(14))
blur = ImageEnhance.Brightness(blur).enhance(0.55)
tint = Image.new("RGB", (W, H), (42, 16, 112))
Image.blend(blur, tint, 0.38).save(os.path.join(out, "backdrop_blur.png"))
# the end card's backdrop: the art itself, lightly darkened at the bottom for the call to action
grad = Image.new("L", (1, H))
for y in range(H):
    grad.putpixel((0, y), int(max(0, (y - H * 0.45) / (H * 0.55)) * 200))
grad = grad.resize((W, H))
dark = Image.new("RGB", (W, H), (20, 8, 50))
Image.composite(dark, art, grad).save(os.path.join(out, "endcard_bg.png"))
print("ok")
