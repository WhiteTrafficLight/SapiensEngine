# Sapiens Engine Scripts

This directory contains utility scripts for development and maintenance of the Sapiens Engine project.

## Indentation Issues Prevention

Python is sensitive to indentation, and switching between different environments or git checkouts can sometimes introduce indentation issues. The scripts in this directory help prevent and fix those issues.

### Pre-commit Hook

The `pre-commit` script checks Python files for syntax errors before committing, focusing on indentation issues. It uses Python's built-in syntax checker and optionally flake8 to validate Python files.

To install the hook manually:

```bash
# Make sure the script is executable
chmod +x scripts/pre-commit

# Create a symlink to .git/hooks directory
ln -sf ../../scripts/pre-commit .git/hooks/pre-commit
```

### Indentation Fixer

The `fix_indentation.py` script automatically finds and fixes common indentation issues in Python files. It also sets up the pre-commit hook.

To use the script:

```bash
# Make sure the script is executable
chmod +x scripts/fix_indentation.py

# Run the script
./scripts/fix_indentation.py
```

This script will:

1. Install necessary dependencies (flake8, black, autopep8)
2. Fix indentation issues in all Python files in the project
3. Set up the pre-commit hook to prevent committing files with syntax errors

## When to Use These Scripts

- **After switching branches**: If you see indentation errors after switching branches or pulling changes
- **Before committing**: The pre-commit hook will run automatically to prevent committing files with syntax errors
- **When restoring from checkpoints**: If you restore code from a checkpoint and encounter indentation issues

## Manual Indentation Fixes

If you encounter indentation issues manually, you can:

1. Check for syntax errors:
   ```bash
   python -m py_compile path/to/file.py
   ```

2. Fix indentation issues with autopep8:
   ```bash
   autopep8 --in-place --aggressive path/to/file.py
   ```

3. Or format code with black:
   ```bash
   black path/to/file.py
   ``` 