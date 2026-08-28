import ast
import io
import os
import tokenize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PY_ROOTS = ['app.py', 'core', 'tests']
JS_ROOTS = [os.path.join('static', 'js'), 'scripts']
CSS_FILES = [os.path.join('static', 'css', 'app.css')]
GO_ROOTS = ['agent']

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'vendor', 'dist', '.vitepress', 'testdata'}

PY_PRAGMAS = ('# noqa', '# type:', '# ruff:', '# pragma:', '# fmt:', '# pylint:')
GO_PRAGMAS = ('//go:', '// +build')


def _walk(rel, exts):
    base = os.path.join(ROOT, rel)
    if os.path.isfile(base):
        yield rel
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(exts):
                yield os.path.relpath(os.path.join(dirpath, name), ROOT)


def _python_offenders():
    found = []
    for rel in _walk('app.py', ('.py',)):
        pass
    for root in PY_ROOTS:
        for rel in _walk(root, ('.py',)):
            path = os.path.join(ROOT, rel)
            with open(path, 'rb') as fh:
                try:
                    for tok in tokenize.tokenize(fh.readline):
                        if tok.type != tokenize.COMMENT:
                            continue
                        text = tok.string.strip()
                        if text.startswith('#!') or text.startswith(PY_PRAGMAS):
                            continue
                        found.append('%s:%d  %s' % (rel, tok.start[0], text[:60]))
                except (tokenize.TokenError, SyntaxError):
                    continue
            try:
                tree = ast.parse(io.open(path, encoding='utf-8').read())
            except SyntaxError:
                continue
            holders = [tree] + [n for n in ast.walk(tree) if isinstance(
                n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            for node in holders:
                body = getattr(node, 'body', [])
                if not body:
                    continue
                first = body[0]
                if not isinstance(first, ast.Expr):
                    continue
                if not isinstance(first.value, ast.Constant):
                    continue
                if not isinstance(first.value.value, str):
                    continue
                label = getattr(node, 'name', '<module>')
                found.append('%s:%d  docstring in %s' % (rel, first.lineno, label))
    return found


def _line_offenders(roots, exts, pragmas=()):
    found = []
    for root in roots:
        for rel in _walk(root, exts):
            path = os.path.join(ROOT, rel)
            in_block = False
            for n, line in enumerate(io.open(path, encoding='utf-8', errors='ignore'), 1):
                text = line.strip()
                if in_block:
                    if '*/' in text:
                        in_block = False
                    continue
                if text.startswith('/*'):
                    if '*/' not in text:
                        in_block = True
                    found.append('%s:%d  %s' % (rel, n, text[:60]))
                    continue
                if text.startswith('//'):
                    if pragmas and text.startswith(pragmas):
                        continue
                    found.append('%s:%d  %s' % (rel, n, text[:60]))
    return found


def _all_offenders():
    return (_python_offenders()
            + _line_offenders(JS_ROOTS, ('.js', '.mjs'))
            + _line_offenders(CSS_FILES, ('.css',))
            + _line_offenders(GO_ROOTS, ('.go',), GO_PRAGMAS))


def test_no_comments_or_docstrings_anywhere():
    offenders = _all_offenders()
    assert not offenders, (
        'code carries %d comment(s) or docstring(s); this project does not use them, '
        'and a docstring is a comment:\n  ' % len(offenders)
        + '\n  '.join(offenders[:60])
        + ('\n  ... and %d more' % (len(offenders) - 60) if len(offenders) > 60 else ''))
