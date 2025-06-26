#!/usr/bin/env python3
"""Install CLASSIC dependencies from requirements.txt"""

import argparse
import subprocess
import sys
from pathlib import Path


def install_requirements(include_gui=False, include_cli=False, include_dev=False):
    """Install requirements based on selected groups."""
    req_file = Path(__file__).parent / "requirements.txt"
    
    if not req_file.exists():
        print(f"Error: {req_file} not found!")
        return 1
    
    requirements = []
    current_section = "core"
    
    with open(req_file) as f:
        for line in f:
            line = line.strip()
            
            if not line or line.startswith('#'):
                if 'GUI dependencies' in line:
                    current_section = "gui"
                elif 'CLI dependencies' in line:
                    current_section = "cli"
                elif 'Development dependencies' in line:
                    current_section = "dev"
                continue
            
            if current_section == "core" or (current_section == "gui" and include_gui) or (current_section == "cli" and include_cli) or (current_section == "dev" and include_dev):
                requirements.append(line)
    
    if not requirements:
        print("No requirements to install.")
        return 0
    
    print(f"Installing {len(requirements)} packages...")
    print("=" * 50)
    
    for req in requirements:
        print(f"Installing: {req}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", req],
            check=False, capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Failed to install {req}")
            print(f"Error: {result.stderr}")
            return 1
    
    print("=" * 50)
    print("All requirements installed successfully!")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Install CLASSIC dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install only core dependencies
  python install_requirements.py

  # Install core + GUI dependencies
  python install_requirements.py --gui

  # Install all dependencies including dev tools
  python install_requirements.py --all
        """
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Include GUI dependencies (PySide6)"
    )
    
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Include CLI dependencies (tqdm)"
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Include development dependencies"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install all dependencies"
    )
    
    args = parser.parse_args()
    
    if args.all:
        args.gui = True
        args.cli = True
        args.dev = True
    
    return install_requirements(
        include_gui=args.gui,
        include_cli=args.cli,
        include_dev=args.dev
    )


if __name__ == "__main__":
    sys.exit(main())