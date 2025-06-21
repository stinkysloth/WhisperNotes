#!/bin/bash

# Exit on error
set -e

# Clean up previous builds
echo "Cleaning up previous builds..."
rm -rf build dist WhisperNotes.spec

# Create a virtual environment for building
echo "Creating a clean virtual environment..."
rm -rf build_env
python3 -m venv build_env
source build_env/bin/activate

# Upgrade pip and setuptools
python -m pip install --upgrade pip setuptools wheel

# Install key packages with PyPI index first
pip install --index-url https://pypi.org/simple \
    more-itertools==10.7.0 \
    pydub==0.25.1 \
    transformers==4.52.4 \
    tiktoken

# Upgrade pip and install wheel
echo "Upgrading pip and installing wheel..."
pip install --upgrade pip wheel setuptools

# Install PyInstaller first
pip install pyinstaller

# Install requirements from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
fi

# Install required packages with versions compatible with Python 3.13
echo "Installing required packages..."
pip install \
    numpy==2.1.2 \
    PySide6==6.9.1 \
    torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu \
    git+https://github.com/openai/whisper.git \
    sounddevice==0.5.2 \
    soundfile==0.13.1 \
    librosa==0.11.0 \
    pydub==0.25.1 \
    transformers==4.52.4 \
    tqdm==4.66.5 \
    requests==2.32.4

# Configure pip to use both PyTorch and PyPI repositories
export PIP_FIND_LINKS="https://download.pytorch.org/whl/cpu https://pypi.org/simple"

# Install more-itertools directly from PyPI
pip install --no-deps more-itertools==10.7.0

# Install additional requirements for whisper
pip install --no-deps --upgrade setuptools wheel

# Install pynput from source as it doesn't have wheels for Python 3.13
echo "Installing pynput from source..."
pip install --no-binary :all: pynput==1.7.6

# Create necessary directories
mkdir -p dist

# Create the PyInstaller spec file
echo "Creating PyInstaller spec file..."
cat > WhisperNotes.spec << 'EOL'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['whisper_notes.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'pynput',
        'pynput.keyboard',
        'pynput.mouse',
        'PySide6',
        'whisper',
        'sounddevice',
        'numpy',
        'librosa',
        'soundfile',
        'pydub',
        'torch',
        'transformers',
        'sentencepiece',
        'tqdm',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WhisperNotes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='entitlements.plist',
)

app = BUNDLE(
    exe,
    name='WhisperNotes.app',
    icon='assets/icon.icns',
    bundle_identifier='com.whispernotes.app',
)
EOL

# Build the application
echo "Building the application..."
pyinstaller --clean --noconfirm WhisperNotes.spec

# Create the DMG
echo "Creating DMG..."
cd dist
hdiutil create -volname "WhisperNotes" -srcfolder WhisperNotes.app -ov -format UDZO WhisperNotes.dmg

echo "\nBuild complete! You can find the DMG in the dist/ directory."
echo "To install: Open the DMG and drag WhisperNotes.app to your Applications folder."
echo "First time running: Right-click the app and select 'Open' to bypass macOS security warnings."
echo "\nIf you encounter any issues, please check the build logs above for errors."
