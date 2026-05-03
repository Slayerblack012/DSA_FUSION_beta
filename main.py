"""
DSA Autograder Unified Launcher - Professional Startup Screen.

Features:
- ASCII art branding
- Component-by-component status check
- Animated progress bar
- Graceful Ctrl+C handling
- Auto-open browser
"""

import os
import socket
import sys
import time
import signal
import webbrowser
import threading
import subprocess
import atexit

# Force UTF-8 output on Windows to avoid UnicodeEncodeError with ASCII arts
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
_shutdown_requested = False
_frontend_process = None


def _stop_frontend_process():
    """Stop the frontend child process started by this launcher."""
    global _frontend_process
    process = _frontend_process
    if process is None:
        return
    if process.poll() is not None:
        _frontend_process = None
        return

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            process.terminate()
            process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
    finally:
        _frontend_process = None


def _setup_signal_handlers():
    """Handle Ctrl+C gracefully."""
    def handle_exit(sig, frame):
        global _shutdown_requested
        if not _shutdown_requested:
            _shutdown_requested = True
            _stop_frontend_process()
            print(f"\n\n  {'=' * 54}")
            print(f"  🛑  Server stopped by user. Goodbye!")
            print(f"  {'=' * 54}\n")
            sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)


# ---------------------------------------------------------------------------
# Color support
# ---------------------------------------------------------------------------
class Colors:
    """ANSI color codes with Windows fallback."""
    _enabled = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    @classmethod
    def _c(cls, code, text):
        if not cls._enabled:
            return text
        # Windows 10+ needs enable VT processing
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
        return f"\033[{code}m{text}\033[0m"

    @classmethod
    def green(cls, text): return cls._c("92", text)
    @classmethod
    def red(cls, text): return cls._c("91", text)
    @classmethod
    def yellow(cls, text): return cls._c("93", text)
    @classmethod
    def cyan(cls, text): return cls._c("96", text)
    @classmethod
    def bold(cls, text): return cls._c("1", text)
    @classmethod
    def dim(cls, text): return cls._c("2", text)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
BANNER = """
+------------------------------------------------------------+
|                                                            |
|   ██████╗ ███████╗████████╗    ███████╗████████╗ █████╗    |
|   ██╔══██╗██╔════╝╚══██╔══╝    ██╔════╝╚══██╔══╝██╔══██╗   |
|   ██║  ██║█████╗     ██║       ███████╗   ██║   ███████║   |
|   ██║  ██║██╔══╝     ██║       ╚════██║   ██║   ██╔══██║   |
|   ██████╔╝███████╗   ██║       ███████║   ██║   ██║  ██║   |
|   ╚═════╝ ╚══════╝   ╚═╝       ╚══════╝   ╚═╝   ╚═╝  ╚═╝   |
|                                                            |
|                  DSA AUTOGRADER                            |
|         AgentWorkBench |Powered by Hưng and Sang           |
|                                                            |
+-----------------------------------------------------------+
"""


def _check_module(name):
    """Check if a Python module is available."""
    try:
        __import__(name)
        return f"{Colors.green('OK')} {name}"
    except ImportError:
        return f"{Colors.red('??')} {name}"


def _print_banner():
    """Print the startup banner with component checks."""
    print(BANNER)
    print(f"  {Colors.bold('Initializing DSA Autograder...')}")
    print(f"  {'-' * 58}")


def _check_dependencies():
    """Check and display dependency status."""
    checks = ["fastapi", "uvicorn", "bcrypt", "jwt", "sqlalchemy", "redis", "psutil", "google", "dotenv"]

    ok_count = 0
    for mod in checks:
        result = _check_module(mod)
        if "OK" in result:
            ok_count += 1
        print(f"    {result}")

    print(f"  {'-' * 58}")
    if ok_count == len(checks):
        print(f"  Dependencies: {Colors.green(f'All {ok_count} modules loaded')}")
    else:
        print(f"  Dependencies: {Colors.yellow(f'{ok_count}/{len(checks)} modules loaded')}")
    print()


def _animated_loading(text, duration=0.5):
    """Show a brief animated spinner (safe against KeyboardInterrupt)."""
    spinner = "|/-\\"
    steps = max(4, int(duration / 0.05))
    delay = duration / steps
    try:
        for i in range(steps):
            ch = spinner[i % len(spinner)]
            sys.stdout.write(f"\r    [{ch}] {text}...")
            sys.stdout.flush()
            time.sleep(delay)
        sys.stdout.write("\r    ")
        sys.stdout.flush()
    except (KeyboardInterrupt, SystemExit):
        sys.stdout.write("\r    \n")
        sys.stdout.flush()
        raise


def _find_venv_python():
    """Find a nearby .venv interpreter."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(os.path.dirname(script_dir), ".venv", "Scripts", "python.exe"),
        os.path.join(os.path.dirname(os.path.dirname(script_dir)), ".venv", "Scripts", "python.exe"),
    ]
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        check = subprocess.run(
            [candidate, "--version"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        if check.returncode == 0:
            return candidate
    return None


def _ensure_venv_python():
    """Re-run this script with .venv Python when launched from system Python."""
    current_executable = os.path.normcase(os.path.abspath(sys.executable))
    if "scripts\\python.exe" in current_executable and ".venv" in current_executable:
        return

    venv_python = _find_venv_python()
    if not venv_python:
        return

    print(f"\n  {Colors.yellow('i')} Switching to virtual env: {Colors.cyan(venv_python)}")
    try:
        # Use subprocess to avoid os.execv issues on Windows with spaces in paths
        process = subprocess.run([venv_python, os.path.abspath(__file__)] + sys.argv[1:])
        sys.exit(process.returncode)
    except Exception as e:
        print(f"  {Colors.red('!!')} Failed to switch to virtual env: {e}")
        sys.exit(1)


def _wait_for_server(host, port, timeout=30):
    """Wait until the server is actually accepting connections."""
    import urllib.request
    url = f"http://{host}:{port}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.urlopen(url, timeout=2)
            if req.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _kill_process_on_port(port: int):
    """Find and terminate any process listening on the given port."""
    import psutil
    import os
    import subprocess
    import time
    
    # 1. Kill the apparent owner of the port (if found)
    try:
        for conn in psutil.net_connections(kind='inet'):
            if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port and conn.status == 'LISTEN':
                pid = conn.pid
                if pid:
                    print(f"  {Colors.yellow('i')} Bắt gặp tiến trình cũ (PID {pid}) đang chiếm cổng {port}. Đang dọn dẹp...")
                    try:
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], 
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else:
                            parent = psutil.Process(pid)
                            children = parent.children(recursive=True)
                            for child in children:
                                child.kill()
                            parent.kill()
                            psutil.wait_procs(children + [parent], timeout=5)
                    except Exception:
                        pass
    except Exception:
        pass

    # 1b. Windows fallback: netstat works in shells where CIM/Get-NetTCPConnection is blocked.
    if os.name == 'nt':
        try:
            output = subprocess.check_output(
                ['netstat', '-ano'],
                text=True,
                stderr=subprocess.DEVNULL,
                encoding='utf-8',
                errors='replace',
            )
            for line in output.splitlines():
                columns = line.split()
                if len(columns) < 5 or columns[0].upper() != 'TCP':
                    continue
                local_address = columns[1]
                state = columns[3].upper()
                pid = columns[4]
                if state == 'LISTENING' and local_address.endswith(f':{port}') and pid.isdigit() and int(pid) != os.getpid():
                    print(f"  {Colors.yellow('i')} Found port {port} owner via netstat (PID {pid}). Stopping it...")
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', pid],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
        except Exception:
            pass

    # 2. Aggressive orphan process hunt
    # Uvicorn worker subprocesses (which hold the port) become ghost nodes if the parent is force killed.
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        my_pid = os.getpid()
        killed_any = False
        for p in psutil.process_iter(['pid', 'name', 'cwd', 'cmdline']):
            try:
                if p.pid == my_pid:
                    continue
                name = (p.info['name'] or '').lower()
                cwd = p.info['cwd'] or ''
                cmdline = ' '.join(p.info['cmdline'] or [])
                
                # if it's a python process from our folder, KILL it.
                if 'python' in name or 'uvicorn' in name:
                    if current_dir in cwd or current_dir in cmdline or 'app.main:app' in cmdline:
                        print(f"  {Colors.dim('-')} Xóa sổ tiến trình kẹt (ghost worker) PID {p.pid}...")
                        p.kill()
                        killed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if killed_any:
            time.sleep(1) # Extra buffer for OS cleanup
    except Exception:
        pass



def _ensure_frontend_built():
    """Ensure the Next.js frontend is built so it can be served."""
    import os
    import subprocess
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    out_dir = os.path.join(frontend_dir, "out")
    if os.path.exists(frontend_dir) and not os.path.exists(out_dir):
        print(f"\n  {Colors.yellow('i')} {Colors.bold('Đang biên dịch giao diện Frontend...')}")
        print(f"    Thư mục 'out' bị thiếu. Quá trình biên dịch chỉ diễn ra 1 lần, tốn khoảng 30s-1p.")
        subprocess.run(["npm", "install"], cwd=frontend_dir, shell=True)
        subprocess.run(["npm", "run", "build"], cwd=frontend_dir, shell=True)
        if os.path.exists(out_dir):
            print(f"  {Colors.green('OK')} Biên dịch Frontend hoàn tất!")
        else:
            print(f"  {Colors.red('!!')} Lỗi biên dịch Frontend. Hãy tự kiểm tra bằng lệnh 'npm run build' trong thư mục frontend.")
        print()


def _frontend_dev_enabled() -> bool:
    """Default to running Next.js dev server with the unified launcher."""
    return os.getenv("START_FRONTEND_DEV", "true").lower() not in {"0", "false", "no", "off"}


def _npm_executable() -> str:
    """Use npm.cmd on Windows to avoid PowerShell execution policy issues."""
    return "npm.cmd" if os.name == "nt" else "npm"


def _start_frontend_dev(port: int = 3000):
    """Start the Next.js frontend dev server in the background."""
    global _frontend_process

    if not _frontend_dev_enabled():
        return None

    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    package_json = os.path.join(frontend_dir, "package.json")
    if not os.path.exists(package_json):
        print(f"  {Colors.yellow('i')} Frontend package.json not found, skipping Next.js dev server.")
        return None

    node_modules = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules):
        print(f"  {Colors.yellow('i')} Installing frontend dependencies...")
        install = subprocess.run([_npm_executable(), "install"], cwd=frontend_dir, shell=False)
        if install.returncode != 0:
            print(f"  {Colors.red('!!')} npm install failed. Frontend dev server was not started.")
            return None

    stdout_path = os.path.join(frontend_dir, "frontend-main.out.log")
    stderr_path = os.path.join(frontend_dir, "frontend-main.err.log")
    stdout = open(stdout_path, "a", encoding="utf-8", errors="replace")
    stderr = open(stderr_path, "a", encoding="utf-8", errors="replace")

    env = os.environ.copy()
    env.setdefault("PORT", str(port))

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    try:
        _frontend_process = subprocess.Popen(
            [_npm_executable(), "run", "dev"],
            cwd=frontend_dir,
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            env=env,
            shell=False,
            creationflags=creationflags,
        )
    except Exception as exc:
        stdout.close()
        stderr.close()
        print(f"  {Colors.red('!!')} Could not start frontend dev server: {exc}")
        return None

    print(f"  {Colors.green('OK')} Frontend dev server starting on http://localhost:{port}")
    print(f"  {Colors.dim('Logs: frontend/frontend-main.out.log and frontend/frontend-main.err.log')}")
    return _frontend_process


def _is_port_open(host: str, port: int) -> bool:
    """Return True when a process is already listening on host:port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.8)
    try:
        return sock.connect_ex((host, port)) == 0
    except OSError:
        return False
    finally:
        sock.close()


def open_browser(host, port):
    """Open browser after server is ready."""
    if _wait_for_server(host, port, timeout=20):
        url = f"http://{host}:{port}"
        print(f"\n  {Colors.green('>>')} Opening browser: {Colors.cyan(url)}")
        try:
            webbrowser.open(url)
        except Exception:
            pass


def open_frontend_browser(host="127.0.0.1", port=3000):
    """Open the frontend browser when the Next.js server is ready."""
    start = time.time()
    while time.time() - start < 30:
        if _is_port_open(host, port):
            url = f"http://localhost:{port}"
            print(f"\n  {Colors.green('>>')} Opening frontend: {Colors.cyan(url)}")
            try:
                webbrowser.open(url)
            except Exception:
                pass
            return
        time.sleep(0.5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    """Entry point for the DSA Fusion launcher."""
    atexit.register(_stop_frontend_process)
    _setup_signal_handlers()
    _ensure_venv_python()

    # Add backend to sys.path
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    sys.path.insert(0, backend_dir)

    # Clear screen and show banner
    os.system('cls' if os.name == 'nt' else 'clear')
    _print_banner()
    _check_dependencies()

    # Animated loading steps
    try:
        _animated_loading("Loading configuration", 0.05)
        _animated_loading("Initializing database", 0.05)
        _animated_loading("Preparing AI-only grading engine", 0.05)
    except (KeyboardInterrupt, SystemExit):
        print(f"\n  Startup cancelled.\n")
        sys.exit(1)

    print(f"    {Colors.green('OK')} {Colors.bold('All systems ready!')}")
    print(f"  {'=' * 58}")
    print(f"  {Colors.cyan('Backend:')}  http://127.0.0.1:8000")
    print(f"  {Colors.cyan('Frontend:')} http://localhost:3000")
    print(f"  {Colors.cyan('Docs:')}     http://127.0.0.1:8000/docs")
    print(f"  {Colors.cyan('Health:')}   http://127.0.0.1:8000/health")
    print(f"  {'=' * 58}")
    print(f"  {Colors.dim('Press CTRL+C to stop the server')}")
    print(f"\n  {Colors.yellow('i')} {Colors.bold('Mẹo:')} Chạy {Colors.cyan('python smart_launcher.py')} để có auto-reconnect!")
    print()

    # Open browser in background after server starts
    host, port = "127.0.0.1", 8000
    frontend_port = 3000

    for used_port in (port, frontend_port):
        if _is_port_open(host, used_port):
            print(f"  {Colors.yellow('i')} Port {used_port} is in use. Cleaning up for a fresh restart...")
            _kill_process_on_port(used_port)
            time.sleep(1)

    if _is_port_open(host, port):
        print(f"  {Colors.yellow('i')} Cổng {port} đang được sử dụng. Tiến hành dọn dẹp để khởi động hoàn toàn mới...")
        _kill_process_on_port(port)
        time.sleep(2)  # allow kernel to free socket completely
        
        if _is_port_open(host, port):
            print(f"  {Colors.red('!!')} Không thể giải phóng sự chiếm dụng ở cổng {port}.")
            print(f"  {Colors.dim('Mẹo: dùng lệnh taskkill hoặc netstat để kiểm tra và đóng thủ công, hoặc khởi động lại máy.')}")
            sys.exit(1)

    if _frontend_dev_enabled():
        _start_frontend_dev(frontend_port)
        threading.Thread(target=open_frontend_browser, args=(host, frontend_port), daemon=True).start()
    else:
        _ensure_frontend_built()
        threading.Thread(target=open_browser, args=(host, port), daemon=True).start()

    # Start uvicorn
    try:
        import uvicorn
        reload_enabled = os.getenv("AUTO_RELOAD", "false").lower() == "true" and os.name != "nt"
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload_enabled,
            reload_dirs=[backend_dir] if reload_enabled else None,
        )
    except KeyboardInterrupt:
        pass
    finally:
        _stop_frontend_process()
        print(f"\n  {'=' * 58}")
        print(f"  Máy chủ đã dừng. Nghỉ Game thôi !")
        print(f"  {'=' * 58}\n")


if __name__ == "__main__":
    main()
