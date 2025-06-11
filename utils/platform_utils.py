"""
Platform-specific utilities for WhisperNotes.

This module provides utility functions for platform-specific operations.
"""

import os
import sys
import logging
import subprocess
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple

logger = logging.getLogger(__name__)

# Platform detection
IS_WINDOWS = sys.platform.startswith('win')
IS_MAC = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

# Platform names for display
PLATFORM_NAMES = {
    'win32': 'Windows',
    'darwin': 'macOS',
    'linux': 'Linux'
}

def get_platform_name() -> str:
    """Get the name of the current platform.
    
    Returns:
        str: Platform name (Windows, macOS, or Linux)
    """
    return PLATFORM_NAMES.get(sys.platform, 'Unknown')

def open_file_explorer(path: Union[str, Path]) -> bool:
    """Open the system file explorer at the specified path.
    
    Args:
        path: Path to open in file explorer
        
    Returns:
        bool: True if the operation was successful, False otherwise
    """
    try:
        path = Path(path).resolve()
        
        if not path.exists():
            logger.error(f"Path does not exist: {path}")
            return False
        
        if IS_WINDOWS:
            os.startfile(path if path.is_file() else path.parent)
        elif IS_MAC:
            subprocess.run(['open', str(path if path.is_file() else path.parent)])
        elif IS_LINUX:
            subprocess.run(['xdg-open', str(path if path.is_file() else path.parent)])
        else:
            logger.error(f"Unsupported platform: {sys.platform}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to open file explorer: {str(e)}", exc_info=True)
        return False

def open_url(url: str) -> bool:
    """Open a URL in the default web browser.
    
    Args:
        url: URL to open
        
    Returns:
        bool: True if the operation was successful, False otherwise
    """
    try:
        import webbrowser
        webbrowser.open(url)
        return True
    except Exception as e:
        logger.error(f"Failed to open URL: {str(e)}", exc_info=True)
        return False

def get_app_data_dir(app_name: str) -> Path:
    """Get the application data directory for the current platform.
    
    Args:
        app_name: Name of the application
        
    Returns:
        Path: Path to the application data directory
    """
    if IS_WINDOWS:
        base_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif IS_MAC:
        base_dir = Path.home() / 'Library' / 'Application Support'
    else:  # Linux and others
        base_dir = Path.home() / '.local' / 'share'
    
    app_dir = base_dir / app_name
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

def get_temp_dir() -> Path:
    """Get the system's temporary directory.
    
    Returns:
        Path: Path to the temporary directory
    """
    return Path(tempfile.gettempdir())

def is_admin() -> bool:
    """Check if the current process has administrator/root privileges.
    
    Returns:
        bool: True if running as admin/root, False otherwise
    """
    try:
        if IS_WINDOWS:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception as e:
        logger.error(f"Failed to check admin status: {str(e)}")
        return False

def run_as_admin() -> bool:
    """Relaunch the current script with administrator/root privileges.
    
    Returns:
        bool: True if the operation was successful, False otherwise
    """
    if is_admin():
        return True
        
    try:
        if IS_WINDOWS:
            import ctypes
            import sys
            
            # Re-run the program with admin rights
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit(0)
            
        elif IS_MAC or IS_LINUX:
            # On macOS/Linux, use sudo to gain root privileges
            os.execvp('sudo', ['sudo', 'python3'] + sys.argv)
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to run as admin: {str(e)}")
        return False

def get_system_info() -> Dict[str, Any]:
    """Get system information.
    
    Returns:
        Dict containing system information
    """
    try:
        import psutil
        import cpuinfo
        
        # Get CPU info
        cpu_info = cpuinfo.get_cpu_info()
        
        # Get memory info
        mem = psutil.virtual_memory()
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        
        return {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
            },
            'cpu': {
                'brand': cpu_info.get('brand_raw', 'Unknown'),
                'arch': cpu_info.get('arch_string_raw', 'Unknown'),
                'hz_actual': cpu_info.get('hz_actual_friendly', 'Unknown'),
                'cores_physical': psutil.cpu_count(logical=False),
                'cores_logical': psutil.cpu_count(logical=True),
            },
            'memory': {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'free': mem.free,
                'percent': mem.percent,
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent,
            },
            'python': {
                'version': platform.python_version(),
                'implementation': platform.python_implementation(),
                'compiler': platform.python_compiler(),
            },
        }
        
    except Exception as e:
        logger.error(f"Failed to get system info: {str(e)}", exc_info=True)
        return {}

def format_bytes(size: int, decimal_places: int = 2) -> str:
    """Format bytes to a human-readable string.
    
    Args:
        size: Size in bytes
        decimal_places: Number of decimal places to show
        
    Returns:
        Formatted string (e.g., "1.23 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            break
        size /= 1024.0
    
    return f"{size:.{decimal_places}f} {unit}"

def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "01:23:45.678")
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"
    else:
        return f"{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"
