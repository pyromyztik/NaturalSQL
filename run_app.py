import os
import sys
import subprocess
import webbrowser
import time

def print_banner():
    banner = r"""
========================================================================
    __  ______  ________  ______  ___    __     _____ ____    __ 
   / | / /   | /_  __/ / / / __ \/   |  / /    / ___// __ \  / / 
  /  |/ / /| |  / / / / / / /_/ / /| | / /     \__ \/ / / / / /  
 / /|  / ___ | / / / /_/ / _, _/ ___ |/ /___  ___/ / /_/ / / /___
/_/ |_/_/  |_|/_/  \____/_/ |_/_/  |_/_____/ /____/\___\_\/_____/

                      NATURALSQL UNIVERSAL
========================================================================
"""
    print(banner)

def main():
    print_banner()

    root_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(root_dir, "frontend", "dist")

    # Ensure frontend build exists
    if not os.path.exists(dist_dir):
        print("[App] Building frontend bundle...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        subprocess.run([npm_cmd, "run", "build"], cwd=os.path.join(root_dir, "frontend"), check=True)
        print("[App] Frontend build complete.")

    url = "http://127.0.0.1:8000"
    print(f"\n[App] Starting NaturalSQL Universal server at: {url}")
    print("[App] Connected Databases Engine ready.")
    print("[App] Press Ctrl+C to stop.\n")

    def open_browser():
        # Wait for the server to be actively accepting connections before opening browser
        import urllib.request
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"{url}/api/health", timeout=1) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.25)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
