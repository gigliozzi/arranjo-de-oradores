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

    if mode == "cron":
        run([sys.executable, "manage.py", "processar_notificacoes"])
        return

    run([sys.executable, "manage.py", "migrate"])
    port = os.getenv("PORT", "8000")
    run(
        [
            "gunicorn",
            "arranjo_oradores.wsgi:application",
            "--bind",
            f"0.0.0.0:{port}",
        ]
    )


if __name__ == "__main__":
    main()
