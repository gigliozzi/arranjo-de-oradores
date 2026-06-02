import os
import subprocess
import sys


def run(command):
    print(f"Running: {' '.join(command)}", flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        sys.exit(completed.returncode)


def main():
    mode = os.getenv("APP_MODE", "web").strip().lower()
    port = os.getenv("PORT", "8000")
    print(f"APP_MODE={mode}", flush=True)
    print(f"PORT={port}", flush=True)

    if mode == "cron":
        run([sys.executable, "manage.py", "processar_notificacoes"])
        return

    run([sys.executable, "manage.py", "migrate"])
    run(
        [
            sys.executable,
            "-m",
            "gunicorn",
            "arranjo_oradores.wsgi:application",
            "--bind",
            f"0.0.0.0:{port}",
            "--workers",
            "1",
            "--timeout",
            "60",
            "--access-logfile",
            "-",
            "--error-logfile",
            "-",
        ]
    )


if __name__ == "__main__":
    main()
