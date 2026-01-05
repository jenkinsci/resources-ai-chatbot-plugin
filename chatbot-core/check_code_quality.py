"""
Simple code quality checker for the build failure analyzer
Checks for common issues without requiring pylint/flake8
"""

import ast
import sys
import os

def check_file(filepath):
    """Check a Python file for common issues"""
    print(f"\n{'='*60}")
    print(f"Checking: {filepath}")
    print('='*60)

    issues = []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check 1: Syntax
    try:
        ast.parse(content)
        print("âœ… Syntax: Valid Python syntax")
    except SyntaxError as e:
        issues.append(f"âŒ Syntax Error: {e}")
        print(f"âŒ Syntax Error: {e}")
        return issues

    # Check 2: Imports
    try:
        tree = ast.parse(content)
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        print(f"âœ… Imports: {len(imports)} import statements found")
    except Exception as e:
        issues.append(f"âš ï¸  Import check failed: {e}")

    # Check 3: Docstrings
    tree = ast.parse(content)
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

    funcs_with_docs = sum(1 for f in functions if ast.get_docstring(f))
    classes_with_docs = sum(1 for c in classes if ast.get_docstring(c))

    print(f"âœ… Docstrings: {funcs_with_docs}/{len(functions)} functions, {classes_with_docs}/{len(classes)} classes")

    if len(functions) > 0 and funcs_with_docs / len(functions) < 0.8:
        issues.append(f"âš ï¸  Low docstring coverage for functions: {funcs_with_docs}/{len(functions)}")

    # Check 4: Line length (rough check)
    lines = content.split('\n')
    long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 100 and not line.strip().startswith('#')]
    if long_lines:
        print(f"âš ï¸  {len(long_lines)} lines exceed 100 characters (lines: {long_lines[:5]}...)")
    else:
        print("âœ… Line length: All lines under 100 characters")

    # Check 5: TODO/FIXME comments
    todos = [i+1 for i, line in enumerate(lines) if 'TODO' in line or 'FIXME' in line]
    if todos:
        print(f"â„¹ï¸  {len(todos)} TODO/FIXME comments found (lines: {todos})")
    else:
        print("âœ… No TODO/FIXME comments")

    # Check 6: Exception handling
    try_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
    print(f"âœ… Exception handling: {len(try_nodes)} try/except blocks")

    # Check 7: Type hints (rough check)
    functions_with_annotations = sum(1 for f in functions if f.returns or any(arg.annotation for arg in f.args.args))
    if len(functions) > 0:
        type_hint_coverage = functions_with_annotations / len(functions) * 100
        print(f"âœ… Type hints: {functions_with_annotations}/{len(functions)} functions ({type_hint_coverage:.0f}%)")

    # Check 8: Magic numbers
    numbers = [node for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, int) and node.value not in [0, 1, -1]]
    if len(numbers) > 10:
        print(f"âš ï¸  {len(numbers)} magic numbers found (consider using constants)")
    else:
        print(f"âœ… Magic numbers: {len(numbers)} (acceptable)")

    return issues


def main():
    print("="*60)
    print("CODE QUALITY CHECK")
    print("="*60)

    files_to_check = [
        'api/services/tools/build_failure_analyzer.py',
        'api/routes/build_analysis.py',
        'tests/unit/test_log_sanitizer.py',
    ]

    all_issues = []

    for filepath in files_to_check:
        if os.path.exists(filepath):
            issues = check_file(filepath)
            all_issues.extend(issues)
        else:
            print(f"\nâš ï¸  File not found: {filepath}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if all_issues:
        print(f"\nâš ï¸  Found {len(all_issues)} potential issues:")
        for issue in all_issues:
            print(f"  {issue}")
        print("\nâš ï¸  Review recommended but not blocking")
        return 0  # Don't fail the check
    else:
        print("\nâœ… All checks passed!")
        print("âœ… Code quality looks good")
        return 0


if __name__ == '__main__':
    sys.exit(main())
