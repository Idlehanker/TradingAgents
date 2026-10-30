#!/usr/bin/env python
"""Start the TradingAgents web stack with one command.

    python scripts/start_web.py            # build the UI once, serve everything on one port
    python scripts/start_web.py --dev      # backend reload + Vite HMR, two ports
    python scripts/start_web.py --check    # only verify prerequisites

Single-port mode (the default) is what a user should run: it builds ``webui/dist`` if
needed and then starts ``webapi``, which serves the API and the built UI from the same
origin — no proxy, no second port, nothing to keep in sync.

Dev mode starts uvicorn with ``--reload`` and the Vite dev server; Vite proxies ``/api``
and ``/ws`` to the backend, so the browser only ever talks to port 5173.

Everything here is stdlib: the script must work before the frontend is built and without
installing anything of its own. It refuses to guess: a missing prerequisite is reported
with the exact command that fixes it.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent.parent
WEBUI = ROOT / "webui"
DIST = WEBUI / "dist"
NODE_MODULES = WEBUI / "node_modules"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8788
UI_PORT = 5173

_INSTALL_HINT = 'pip install -e ".[web]"   (from the repository root; from webapi/ use pip install -e "..[web]"'


def _say(message: str) -> None:
    print(f"[start] {message}", flush=True)


def _die(message: str, code: int = 2) -> NoReturn:
    print(f"[start] ERROR: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def _npm() -> str | None:
    """The npm launcher for this platform, or None when it is not installed."""
    for name in ("npm.cmd", "npm"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _have_web_extra() -> bool:
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError:
        return False
    return True


def _check() -> list[tuple[str, bool, str]]:
    """Every prerequisite, and what to do about the missing ones."""
    npm = _npm()
    rows = [
        ("python web extra (fastapi, uvicorn)", _have_web_extra(), _INSTALL_HINT),
        ("node / npm", bool(npm), "install Node 18+ and put npm on PATH"),
        ("webui/node_modules", NODE_MODULES.is_dir(), "npm install   (in webui/)"),
        ("webui/dist (built UI)", DIST.is_dir(), "npm run build   (in webui/), or drop --no-build"),
    ]
    return [(name, ok, hint if not ok else "") for name, ok, hint in rows]


def _print_check(rows: list[tuple[str, bool, str]]) -> bool:
    for name, ok, hint in rows:
        mark = "ok  " if ok else "MISS"
        print(f"  [{mark}] {name}" + (f"  ->  {hint}" if hint else ""), flush=True)
    return all(ok for _, ok, _ in rows)


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> int:
    """Run a child to completion, streaming its output."""
    _say("$ " + " ".join(cmd) + f"   (in {cwd.name})")
    completed = subprocess.run(cmd, cwd=str(cwd), env=env)
    return completed.returncode


def _ensure_node_modules(env: dict[str, str], skip_install: bool) -> None:
    if NODE_MODULES.is_dir():
        return
    npm = _npm()
    if npm is None:
        _die("npm is not on PATH; install Node 18+ to build or run the dashboard")
    if skip_install:
        _die(f"{NODE_MODULES} is missing and --skip-install was given; run npm install in webui/")
    _say("installing frontend dependencies (first run only)")
    if _run([npm, "install"], WEBUI, env) != 0:
        _die("npm install failed", 1)


def _build(env: dict[str, str]) -> None:
    npm = _npm()
    if npm is None:
        _die("npm is not on PATH; cannot build the dashboard")
    _say("building the dashboard into webui/dist")
    if _run([npm, "run", "build"], WEBUI, env) != 0:
        _die("npm run build failed", 1)


def _pump(prefix: str, stream, sink) -> None:
    """Prefix a child's output so two servers stay readable in one terminal."""
    for raw in iter(stream.readline, ""):
        sink.write(f"[{prefix}] {raw}")
        sink.flush()
    stream.close()


def _start_children(specs: list[tuple[str, list[str], Path, dict[str, str]]]) -> int:
    """Start every (name, argv, cwd, env), stream their output, stop them together."""
    children: list[tuple[str, subprocess.Popen]] = []
    for name, argv, cwd, env in specs:
        _say(f"starting {name}: " + " ".join(argv))
        try:
            child = subprocess.Popen(
                argv,
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            for _, started in children:
                started.terminate()
            _die(f"could not start {name}: {exc}", 1)
        children.append((name, child))
        threading.Thread(target=_pump, args=(name, child.stdout, sys.stdout), daemon=True).start()

    _say("press Ctrl+C to stop")
    try:
        while True:
            for name, child in children:
                code = child.poll()
                if code is not None:
                    _say(f"{name} exited with code {code}; stopping the rest")
                    return code
            time.sleep(0.4)
    except KeyboardInterrupt:
        _say("stopping")
        return 0
    finally:
        for _, child in children:
            if child.poll() is None:
                child.terminate()
        for name, child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _say(f"{name} ignored terminate; killing it")
                child.kill()
                child.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="start_web.py",
        description="Start the TradingAgents web dashboard (single port by default).",
    )
    parser.add_argument("--dev", action="store_true", help="backend reload + Vite dev server on 5173")
    parser.add_argument("--host", default=os.getenv("TRADINGAGENTS_WEB_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.getenv("TRADINGAGENTS_WEB_PORT", DEFAULT_PORT)))
    parser.add_argument("--no-build", action="store_true", help="serve the existing webui/dist; never build")
    parser.add_argument("--skip-install", action="store_true", help="never run npm install")
    parser.add_argument("--check", action="store_true", help="report prerequisites and exit")
    args = parser.parse_args(argv)

    os.chdir(ROOT)
    env = dict(os.environ)
    env["TRADINGAGENTS_WEB_HOST"] = args.host
    env["TRADINGAGENTS_WEB_PORT"] = str(args.port)

    if args.check:
        _say(f"repository root: {ROOT}")
        if _print_check(_check()):
            _say("everything needed is present")
            return 0
        _say("some prerequisites are missing (see the hints above)")
        return 1

    if not _have_web_extra():
        _die("the [web] extra is not installed -> " + _INSTALL_HINT)

    if args.dev:
        _ensure_node_modules(env, args.skip_install)
        # The browser, not the server, resolves this: 0.0.0.0 is not dialable.
        proxy_host = "127.0.0.1" if args.host in ("0.0.0.0", "::", "") else args.host
        env["VITE_BACKEND"] = f"http://{proxy_host}:{args.port}"
        backend = [sys.executable, "-m", "uvicorn", "webapi.server:app",
                   "--host", args.host, "--port", str(args.port), "--reload"]
        npm = _npm()
        if npm is None:
            _die("npm is not on PATH; --dev needs the Vite dev server")
        frontend = [npm, "run", "dev"]
        _say(f"backend http://{args.host}:{args.port}  |  dashboard http://localhost:{UI_PORT}")
        return _start_children([
            ("api", backend, ROOT, env),
            ("ui", frontend, WEBUI, env),
        ])

    if not DIST.is_dir():
        if args.no_build:
            _die("webui/dist does not exist and --no-build was given; run npm run build in webui/")
        _ensure_node_modules(env, args.skip_install)
        _build(env)

    _say(f"dashboard: http://{args.host}:{args.port}   (API docs: /api/docs)")
    return _start_children([
        ("api", [sys.executable, "-m", "webapi.server"], ROOT, env),
    ])


if __name__ == "__main__":
    raise SystemExit(main())
