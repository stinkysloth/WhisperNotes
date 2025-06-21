#!/usr/bin/env python3
"""
Convert a PNG file to ICNS format for macOS applications.
Usage: python create_icns.py input.png output.icns
"""
import os
import sys
import subprocess
import tempfile
import shutil

def create_icns(input_png, output_icns):
    """Convert a PNG to ICNS format."""
    # Create a temporary directory for the iconset
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create iconset directory structure
        iconset = os.path.join(temp_dir, 'AppIcon.iconset')
        os.makedirs(iconset)
        
        # Define icon sizes needed for macOS
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        
        # Generate all required sizes
        for size in sizes:
            # Normal size
            output_file = os.path.join(iconset, f'icon_{size}x{size}.png')
            subprocess.run([
                'sips',
                '-z', str(size), str(size),
                input_png,
                '--out', output_file
            ], check=True)
            
            # Retina (@2x) size
            if size < 1024:  # No @3x for 1024px
                retina_size = size * 2
                retina_file = os.path.join(iconset, f'icon_{size}x{size}@2x.png')
                subprocess.run([
                    'sips',
                    '-z', str(retina_size), str(retina_size),
                    input_png,
                    '--out', retina_file
                ], check=True)
        
        # Create the .icns file
        if os.path.exists(output_icns):
            os.remove(output_icns)
            
        subprocess.run([
            'iconutil',
            '-c', 'icns',
            '-o', output_icns,
            iconset
        ], check=True)
        
        print(f"Successfully created {output_icns}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating ICNS file: {e}")
        return False
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python create_icns.py input.png output.icns")
        sys.exit(1)
    
    input_png = sys.argv[1]
    output_icns = sys.argv[2]
    
    if not os.path.exists(input_png):
        print(f"Error: Input file '{input_png}' not found.")
        sys.exit(1)
    
    if not create_icns(input_png, output_icns):
        sys.exit(1)
