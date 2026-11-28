"""Conservative heuristics for common weak Python verifier assertions."""

import ast


def _name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ''


def _intersection(node):
    return any(
        isinstance(part, ast.BinOp) and isinstance(part.op, ast.BitAnd)
        or isinstance(part, ast.Call) and _name(part.func) == 'intersection'
        for part in ast.walk(node)
    )


def _lower_bound(node):
    return isinstance(node, ast.Compare) and any(isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) for op in node.ops)


def python_verifier_warnings(root):
    warnings = []
    for path in sorted((root / 'tests').rglob('*.py')):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, SyntaxError):
            continue
        relative = path.relative_to(root).as_posix()
        scopes = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        scopes.append(tree)
        for scope in scopes:
            # Module-level checks exclude function bodies, which are inspected separately.
            body = scope.body
            nodes = [part for statement in body if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for part in ast.walk(statement)]
            assignments = {}
            for node in nodes:
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name):
                            assignments[target.id] = node.value
            def has_intersection(node, seen=None):
                seen = set() if seen is None else seen
                if _intersection(node):
                    return True
                for part in ast.walk(node):
                    if isinstance(part, ast.Name) and part.id in assignments and part.id not in seen:
                        seen.add(part.id)
                        if assignments[part.id] is not None and has_intersection(assignments[part.id], seen):
                            return True
                return False
            checks = [node.test for node in nodes if isinstance(node, (ast.Assert, ast.If, ast.IfExp, ast.While))]
            checks.extend(node for node in nodes if isinstance(node, ast.Call) and _name(node.func) in {'assertEqual', 'assertIn', 'assertTrue'})
            exact = any(isinstance(node, ast.Compare) and any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops) and (has_intersection(node) or any(isinstance(part, ast.Call) and _name(part.func) in {'set', 'symmetric_difference', 'difference'} for part in ast.walk(node))) for check in checks for node in ast.walk(check))
            for check in checks:
                for node in ast.walk(check):
                    if _lower_bound(node) and has_intersection(node) and not exact:
                        warnings.append(f'HE-005: {relative}:{node.lineno}: intersection threshold may accept extra elements; compare the complete sets or penalize extras')
            # Only report checks that actually assert stdout or file existence, not mere reads.
            calls = [node for node in nodes if isinstance(node, ast.Call)]
            call_names = {_name(call.func) for call in calls}
            for check in checks:
                parts = list(ast.walk(check))
                stdout = any(isinstance(part, ast.Attribute) and part.attr == 'stdout' or isinstance(part, ast.Name) and part.id == 'stdout' for part in parts)
                existence = any(isinstance(part, ast.Call) and _name(part.func) in {'exists', 'is_file', 'isfile'} for part in parts)
                if stdout and not any(name.startswith('assert_') and name not in {'assert_equal', 'assert_in'} for name in call_names) and not any(isinstance(part, ast.Attribute) and part.attr in {'returncode', 'called', 'call_count', 'call_args'} for node in checks for part in ast.walk(node)):
                    warnings.append(f'HE-006: {relative}:{check.lineno}: stdout-only check may miss side effects; assert the real call or resulting state')
                if existence and not call_names.intersection({'load', 'loads', 'verify', 'verify_signature', 'check_signature', 'digest', 'hexdigest'}):
                    warnings.append(f'HE-006: {relative}:{check.lineno}: file existence alone does not validate contents; parse the format and verify integrity or signatures')
    return list(dict.fromkeys(warnings))
