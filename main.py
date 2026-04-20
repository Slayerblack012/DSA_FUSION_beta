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


def _setup_signal_handlers():
    """Handle Ctrl+C gracefully."""
    def handle_exit(sig, frame):
        global _shutdown_requested
        if not _shutdown_requested:
            _shutdown_requested = True
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    """Entry point for the DSA Fusion launcher."""
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
        _animated_loading("Preparing grading engine", 0.05)
    except (KeyboardInterrupt, SystemExit):
        print(f"\n  Startup cancelled.\n")
        sys.exit(1)

    print(f"    {Colors.green('OK')} {Colors.bold('All systems ready!')}")
    print(f"  {'=' * 58}")
    print(f"  {Colors.cyan('Server:')}  http://127.0.0.1:8000")
    print(f"  {Colors.cyan('Docs:')}    http://127.0.0.1:8000/docs")
    print(f"  {Colors.cyan('Health:')}  http://127.0.0.1:8000/health")
    print(f"  {'=' * 58}")
    print(f"  {Colors.dim('Press CTRL+C to stop the server')}")
    print(f"\n  {Colors.yellow('i')} {Colors.bold('Mẹo:')} Chạy {Colors.cyan('python smart_launcher.py')} để có auto-reconnect!")
    print()

    _ensure_frontend_built()

    # Open browser in background after server starts
    host, port = "127.0.0.1", 8000

    if _is_port_open(host, port):
        print(f"  {Colors.yellow('i')} Cổng {port} đang được sử dụng. Tiến hành dọn dẹp để khởi động hoàn toàn mới...")
        _kill_process_on_port(port)
        time.sleep(2)  # allow kernel to free socket completely
        
        if _is_port_open(host, port):
            print(f"  {Colors.red('!!')} Không thể giải phóng sự chiếm dụng ở cổng {port}.")
            print(f"  {Colors.dim('Mẹo: dùng lệnh taskkill hoặc netstat để kiểm tra và đóng thủ công, hoặc khởi động lại máy.')}")
            sys.exit(1)

    threading.Thread(target=open_browser, args=(host, port), daemon=True).start()

    # Start uvicorn
    try:
        import uvicorn
        uvicorn.run("app.main:app", host=host, port=port, reload=True, reload_dirs=[backend_dir])
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n  {'=' * 58}")
        print(f"  Máy chủ đã dừng. Nghỉ Game thôi !")
        print(f"  {'=' * 58}\n")


if __name__ == "__main__":
    main()
