"""Guard dependency direction, without importing frameworks or a database."""
import ast
from importlib.util import resolve_name
from pathlib import Path
import subprocess
import sys


def test_core_has_no_technical_dependencies():
    root = Path(__file__).resolve().parents[1]
    for folder in ('domain', 'application'):
        allowed = ('app.domain',) if folder == 'domain' else ('app.domain', 'app.application')
        for path in (root / 'app' / folder).rglob('*.py'):
            relative = path.relative_to(root).with_suffix('')
            package = '.'.join(relative.parts[:-1])
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [x.name for x in node.names]
                elif isinstance(node, ast.ImportFrom):
                    module = '.' * node.level + (node.module or '')
                    modules = [resolve_name(module, package) if node.level else module]
                else:
                    continue
                for module in modules:
                    assert (module.split('.')[0] in sys.stdlib_module_names
                            or any(module == prefix or module.startswith(prefix + '.') for prefix in allowed)), (path, module)


def test_core_imports_without_fastapi_sqlalchemy_or_pydantic():
    code = '''import sys
from app.domain import model
from app.application.service import FestiPlan
assert not {'fastapi', 'sqlalchemy', 'pydantic'} & sys.modules.keys()
'''
    subprocess.run([sys.executable, '-c', code], check=True, cwd=Path(__file__).resolve().parents[1])
