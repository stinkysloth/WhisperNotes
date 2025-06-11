"""
Script to create a simple application icon for WhisperNotes.
"""
import os
from PIL import Image, ImageDraw, ImageFont

def create_icon():
    # Create a 512x512 image with a blue background
    size = 512
    img = Image.new('RGBA', (size, size), (65, 105, 225, 255))  # Royal blue
    draw = ImageDraw.Draw(img)
    
    # Draw a white microphone icon (simple circle with line)
    margin = 100
    circle_bbox = [margin, margin, size - margin, size - margin]
    draw.ellipse(circle_bbox, outline='white', width=20)
    
    # Draw a microphone stand
    stand_width = 40
    stand_height = 150
    stand_x = size // 2 - stand_width // 2
    stand_y = size - margin - stand_height
    draw.rectangle(
        [stand_x, stand_y, stand_x + stand_width, stand_y + stand_height],
        fill='white'
    )
    
    # Save the icon
    os.makedirs('assets', exist_ok=True)
    icon_path = 'assets/icon.png'
    img.save(icon_path)
    print(f"Icon created at: {icon_path}")
    return icon_path

if __name__ == "__main__":
    create_icon()
