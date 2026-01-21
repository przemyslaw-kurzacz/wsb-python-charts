"""pytest fixtures for Data Charts Flask app."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

import pytest

from app import create_app
from app.models import User


@pytest.fixture()
def app(tmp_path: Path):
    app = create_app()

    db_path = tmp_path / "db.json"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret-key",
        DATABASE_PATH=str(db_path),
        UPLOAD_FOLDER=str(upload_dir),
        MAX_CONTENT_LENGTH=256 * 1024,  # 256KB
    )
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def register_user(client) -> Callable[[str, str, str], "pytest.Wrapper"]:
    def _register(username: str, password: str, password2: str | None = None):
        return client.post(
            "/auth/register",
            data={
                "username": username,
                "password": password,
                "password2": password2 if password2 is not None else password,
            },
            follow_redirects=True,
        )
    return _register


@pytest.fixture()
def login_user(client) -> Callable[[str, str], "pytest.Wrapper"]:
    def _login(username: str, password: str):
        return client.post(
            "/auth/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )
    return _login


@pytest.fixture()
def test_user(app) -> Dict[str, str]:
    with app.app_context():
        username = "testuser"
        password = "testpass123"
        User.create_user(username, password)
    return {"username": username, "password": password}


@pytest.fixture()
def authenticated_client(client, login_user, test_user):
    resp = login_user(test_user["username"], test_user["password"])
    assert resp.status_code == 200
    return client


@pytest.fixture()
def csv_bytes() -> Callable[[str], bytes]:
    def _csv(content: str) -> bytes:
        return content.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return _csv


# === BENTLEY_FIXTURES_START ===
# Fixtures + helpery do auto-detekcji implementacji Algorytmu Bentleya.
# Jeśli chcesz wymusić konkretny moduł/funkcję:
#   set BENTLEY_MODULE="app.algorithms.bentley_ottmann"
#   set BENTLEY_FUNC="bentley_ottmann"
# w PowerShell:
#   $env:BENTLEY_MODULE="..."
#   $env:BENTLEY_FUNC="..."

import os
import sys
import importlib
import inspect
from typing import Any, Iterable, Tuple, Set


def _iter_candidate_modules(repo_root: Path) -> list[str]:
    """
    Szuka plików zawierających bentley/ottmann/sweep.
    Zwraca listę modułów do importu w stylu pythonowym (np. app.algorithms.bentley_ottmann)
    """
    candidates: list[str] = []
    search_dirs = [repo_root / "app", repo_root / "src"]
    patterns = ("bentley", "ottmann", "sweep", "line_sweep", "intersections")

    for d in search_dirs:
        if not d.exists():
            continue
        for py in d.rglob("*.py"):
            name = py.name.lower()
            if any(p in name for p in patterns):
                rel = py.relative_to(repo_root)
                mod = ".".join(rel.with_suffix("").parts)
                candidates.append(mod)

    # też dopuszczamy "app.main.processing" jeśli ktoś wrzucił tam logikę
    if (repo_root / "app" / "main" / "processing.py").exists():
        candidates.append("app.main.processing")

    # uniq stable order
    uniq: list[str] = []
    for m in candidates:
        if m not in uniq:
            uniq.append(m)
    return uniq


def _find_callable_in_module(module: Any) -> Callable:
    """
    Szuka funkcji algorytmu po nazwach typowych.
    """
    preferred_names = [
        "bentley_ottmann",
        "bentley",
        "find_intersections",
        "compute_intersections",
        "intersections",
        "sweep_line",
    ]

    for name in preferred_names:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn

    # fallback: jeśli w module jest jedna sensowna funkcja publiczna z parametrem segments
    funcs = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("_"):
            continue
        sig = inspect.signature(obj)
        if len(sig.parameters) >= 1:
            funcs.append((name, obj))

    if len(funcs) == 1:
        return funcs[0][1]

    raise RuntimeError(
        f"Nie znaleziono funkcji algorytmu w module {module.__name__}. "
        f"Ustaw BENTLEY_MODULE/BENTLEY_FUNC."
    )


def _resolve_bentley_callable(repo_root: Path) -> Callable:
    env_mod = os.environ.get("BENTLEY_MODULE")
    env_fn = os.environ.get("BENTLEY_FUNC")

    # ensure repo root in sys.path
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    if env_mod:
        mod = importlib.import_module(env_mod)
        if env_fn:
            fn = getattr(mod, env_fn)
            if not callable(fn):
                raise RuntimeError(f"{env_mod}.{env_fn} nie jest callable.")
            return fn
        return _find_callable_in_module(mod)

    # auto-detect
    for mod_name in _iter_candidate_modules(repo_root):
        try:
            mod = importlib.import_module(mod_name)
            fn = _find_callable_in_module(mod)
            return fn
        except Exception:
            continue

    raise RuntimeError(
        "Nie mogę znaleźć implementacji Algorytmu Bentleya. "
        "Dodaj plik bentley_ottmann.py / bentley.py albo ustaw ENV BENTLEY_MODULE/BENTLEY_FUNC."
    )


def _normalize_points(result: Any, ndigits: int = 6) -> Set[Tuple[float, float]]:
    """
    Normalizuje wynik algorytmu do set[(x,y)].
    Obsługuje:
    - set/list/tuple/generator punktów
    - dict (bierzemy keys)
    Punkt może być:
    - (x, y)
    - obiekt z .x .y
    """
    if result is None:
        return set()

    if isinstance(result, dict):
        iterable = result.keys()
    else:
        iterable = result

    pts: Set[Tuple[float, float]] = set()
    for item in iterable:
        x = y = None
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            x, y = item[0], item[1]
        else:
            # object with x/y
            if hasattr(item, "x") and hasattr(item, "y"):
                x, y = getattr(item, "x"), getattr(item, "y")

        if x is None or y is None:
            raise TypeError(
                f"Nie umiem znormalizować elementu wyniku: {item!r}. "
                f"Wynik ma być punktami (x,y) lub obiektami z .x/.y."
            )

        pts.add((round(float(x), ndigits), round(float(y), ndigits)))
    return pts


@pytest.fixture()
def bentley_callable(request) -> Callable:
    """
    Fixture zwraca funkcję algorytmu Bentleya.
    """
    repo_root = Path(request.config.rootpath)
    return _resolve_bentley_callable(repo_root)


@pytest.fixture()
def norm_points() -> Callable:
    return _normalize_points
# === BENTLEY_FIXTURES_END ===
