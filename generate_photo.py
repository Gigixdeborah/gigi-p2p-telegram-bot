from PIL import Image, ImageDraw, ImageFont
import math
import numpy as np

# Create a square base image (dark background)
size = 512
base = Image.new("RGBA", (size, size), (10, 10, 10, 255))

# Create a radial gradient overlay
arr = np.zeros((size, size, 4), dtype=np.uint8)
center = size // 2
max_radius = center

for y in range(size):
    for x in range(size):
        dx = x - center
        dy = y - center
        r = math.sqrt(dx * dx + dy * dy)
        if r < max_radius:
            alpha = int(255 * (1 - r / max_radius))  # Gradient effect
            arr[y, x] = (30, 144, 255, alpha)  # DodgerBlue color
        else:
            arr[y, x] = (10, 10, 10, 255)

gradient = Image.fromarray(arr, mode="RGBA")

# Composite the gradient on top of the base image
userphoto = Image.alpha_composite(base, gradient)

# Draw the bot name in the center
draw = ImageDraw.Draw(userphoto)
text = "GigiP2Bot"

try:
    # Use Arial or default font
    font = ImageFont.truetype("arial.ttf", 40)
except IOError:
    font = ImageFont.load_default()

# Get text size using textbbox() instead of textsize()
bbox = draw.textbbox((0, 0), text, font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]

# Position the text in the center
text_x = (size - text_w) / 2
text_y = (size - text_h) / 2
draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

# Save the image
userphoto.save("gigiP2bot_userphoto.png")
userphoto.show()

print("✅ Profile image 'gigiP2bot_userphoto.png' created successfully!")
