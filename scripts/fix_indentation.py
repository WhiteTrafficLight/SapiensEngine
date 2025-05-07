#!/usr/bin/env python3
"""
Fix Python indentation issues in the project and set up git hooks.

This script performs the following tasks:
1. Fixes common indentation issues in Python files
2. Sets up the pre-commit hook to prevent committing files with syntax errors
3. Installs necessary dependencies for validation if needed
"""

import os
import subprocess
import sys
from pathlib import Path
import re

# Project root (assuming the script is in scripts/ directory)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

def install_dependencies():
    """Install necessary dependencies for validation"""
    print("Checking and installing necessary dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "flake8", "black", "autopep8"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print(e.stderr.decode())

def setup_git_hooks():
    """Set up the pre-commit hook"""
    print("Setting up pre-commit hook...")
    
    # Path to git hooks directory
    git_hooks_dir = PROJECT_ROOT / ".git" / "hooks"
    
    # Path to our pre-commit hook script
    pre_commit_script = PROJECT_ROOT / "scripts" / "pre-commit"
    
    # Path to git pre-commit hook
    git_pre_commit = git_hooks_dir / "pre-commit"
    
    if not git_hooks_dir.exists():
        print(f"❌ Git hooks directory not found at {git_hooks_dir}")
        print("Make sure you're running this script from the project root and .git exists")
        return False
    
    # Create symlink or copy the file
    try:
        # Remove existing hook if it exists
        if git_pre_commit.exists():
            git_pre_commit.unlink()
        
        # Try creating a symlink first
        try:
            # Use relative path for the symlink target
            rel_path = os.path.relpath(pre_commit_script, git_hooks_dir)
            os.symlink(rel_path, git_pre_commit)
            print(f"✅ Created symlink to pre-commit hook")
        except OSError:
            # If symlink fails (e.g., on Windows), copy the file
            import shutil
            shutil.copy2(pre_commit_script, git_pre_commit)
            # Make sure it's executable
            git_pre_commit.chmod(0o755)
            print(f"✅ Copied pre-commit hook to {git_pre_commit}")
            
        return True
    except Exception as e:
        print(f"❌ Failed to set up pre-commit hook: {e}")
        return False

def fix_indentation_in_file(file_path):
    """Fix indentation issues in a single Python file"""
    print(f"Checking indentation in {file_path}...")
    
    # First, check for syntax errors
    try:
        # Try to compile the file to check for syntax errors
        subprocess.run([sys.executable, "-m", "py_compile", str(file_path)], 
                      check=True, capture_output=True)
        print(f"  ✅ No syntax errors found in {file_path}")
    except subprocess.CalledProcessError:
        print(f"  ❌ Syntax errors found in {file_path}")
        
        # Try to fix with autopep8 first (handles indentation well)
        try:
            subprocess.run(["autopep8", "--in-place", "--aggressive", str(file_path)], 
                          check=True, capture_output=True)
            print(f"  ✅ Applied autopep8 fixes to {file_path}")
            
            # Check if fixes resolved the issue
            try:
                subprocess.run([sys.executable, "-m", "py_compile", str(file_path)], 
                              check=True, capture_output=True)
                print(f"  ✅ Syntax errors fixed in {file_path}")
                return True
            except subprocess.CalledProcessError:
                print(f"  ❌ autopep8 didn't fix all syntax errors in {file_path}")
                
                # Try with black as a last resort
                try:
                    subprocess.run(["black", str(file_path)], 
                                  check=True, capture_output=True)
                    print(f"  ✅ Applied black formatting to {file_path}")
                    
                    # Check if fixes resolved the issue
                    try:
                        subprocess.run([sys.executable, "-m", "py_compile", str(file_path)], 
                                      check=True, capture_output=True)
                        print(f"  ✅ Syntax errors fixed by black in {file_path}")
                        return True
                    except subprocess.CalledProcessError:
                        print(f"  ❌ Automatic fixes failed for {file_path}")
                        return False
                except subprocess.CalledProcessError as e:
                    print(f"  ❌ Black formatting failed: {e}")
                    return False
        except subprocess.CalledProcessError as e:
            print(f"  ❌ autopep8 failed: {e}")
            return False
    
    # Check for indentation issues with flake8
    try:
        result = subprocess.run(
            ["flake8", "--select=E111,E112,E113,E114,E115,E116,E117", str(file_path)],
            capture_output=True, text=True, check=False
        )
        
        if result.stdout.strip():
            print(f"  ⚠️ Indentation issues found with flake8 in {file_path}")
            print(result.stdout)
            
            # Try to fix with autopep8
            try:
                subprocess.run(["autopep8", "--in-place", "--select=E111,E112,E113,E114,E115,E116,E117", 
                               str(file_path)], check=True, capture_output=True)
                print(f"  ✅ Applied indentation fixes to {file_path}")
                return True
            except subprocess.CalledProcessError as e:
                print(f"  ❌ autopep8 failed: {e}")
                return False
        else:
            print(f"  ✅ No indentation issues found with flake8 in {file_path}")
            return True
    except Exception as e:
        print(f"  ❌ flake8 check failed: {e}")
        return False

def fix_specific_indentation_issues(file_path):
    """Fix specific indentation issues that may not be caught by standard tools"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for common indentation problematic patterns
        lines = content.split('\n')
        fixed_lines = []
        is_modified = False
        
        # Pattern 1: Inconsistent indentation after control statements
        in_block = False
        expected_indent = 0
        
        for i, line in enumerate(lines):
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith('#'):
                fixed_lines.append(line)
                continue
                
            # Count leading spaces
            leading_spaces = len(line) - len(line.lstrip())
            
            # Check for control statements that should increase indent level
            if re.search(r':\s*$', line) and not line.strip().startswith(('else', 'elif', 'except', 'finally')):
                in_block = True
                expected_indent = leading_spaces + 4  # Python standard is 4 spaces
            
            # Check if indentation is incorrect in a block
            if in_block and line.strip() and leading_spaces != expected_indent:
                if i > 0 and lines[i-1].strip().endswith(':'):
                    # This is the first line after a control statement, should be indented
                    fixed_line = ' ' * expected_indent + line.lstrip()
                    fixed_lines.append(fixed_line)
                    is_modified = True
                    print(f"  🔧 Fixed indentation at line {i+1}")
                    continue
            
            # Check for block exit
            if in_block and leading_spaces < expected_indent and line.strip():
                in_block = False
            
            fixed_lines.append(line)
        
        # If modifications were made, write back the file
        if is_modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
            print(f"  ✅ Fixed specific indentation issues in {file_path}")
            return True
        else:
            print(f"  ✅ No specific indentation issues found in {file_path}")
            return False
    
    except Exception as e:
        print(f"  ❌ Error fixing specific indentation issues: {e}")
        return False

def fix_all_python_files():
    """Find and fix indentation in all Python files in the project"""
    print("Fixing indentation in all Python files...")
    
    # Find all Python files in the project
    python_files = list(PROJECT_ROOT.glob('**/*.py'))
    
    fixed_files = 0
    error_files = 0
    
    for file_path in python_files:
        # Skip files in .git, venv, or __pycache__ directories
        if any(part in str(file_path) for part in ['.git', 'venv', '__pycache__']):
            continue
        
        try:
            # Try general indentation fixes
            fixed1 = fix_indentation_in_file(file_path)
            
            # Try specific indentation pattern fixes
            fixed2 = fix_specific_indentation_issues(file_path)
            
            if fixed1 or fixed2:
                fixed_files += 1
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            error_files += 1
    
    print(f"\n✅ Processed {len(python_files)} Python files")
    print(f"✅ Fixed indentation in {fixed_files} files")
    if error_files > 0:
        print(f"❌ Encountered errors in {error_files} files")

def main():
    """Main function"""
    print("=== Python Indentation Fixer and Git Hook Setup ===")
    
    # Install dependencies
    install_dependencies()
    
    # Fix indentation in all Python files
    fix_all_python_files()
    
    # Set up git hooks
    setup_git_hooks()
    
    print("\n=== All done! ===")
    print("Your Python files have been checked for indentation issues.")
    print("A pre-commit hook has been set up to prevent committing files with syntax errors.")
    print("\nTo manually check a file for syntax errors, run:")
    print("  python -m py_compile path/to/file.py")
    print("\nTo manually fix indentation in a file, run:")
    print("  autopep8 --in-place --aggressive path/to/file.py")
    print("  or")
    print("  black path/to/file.py")

if __name__ == "__main__":
    main() 