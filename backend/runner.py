import os, subprocess, tempfile, shlex, uuid

# Toggle via env: DOCKER_SANDBOX=1 → run inside ephemeral containers
USE_DOCKER = os.getenv("DOCKER_SANDBOX", "0") == "1"

LANG_HOST = {
    "python": {"ext": ".py", "cmd": "python3 {file}"},
    "javascript": {"ext": ".js", "cmd": "node {file}"},
    "r": {"ext": ".R", "cmd": "Rscript {file}"},
    "bash": {"ext": ".sh", "cmd": "bash {file}"},
}

LANG_IMAGE = {
    "python": "python:3.11-alpine",
    "javascript": "node:20-alpine",
    "r": "r-base:4.3.1",      # or rocker/r-base
    "bash": "alpine:3.20",
}

LANG_CMD_IN_CONTAINER = {
    "python": "python3 /work/main.py",
    "javascript": "node /work/main.js",
    "r": "Rscript /work/main.R",
    "bash": "sh /work/main.sh",
}

def _run_shell(cmd: str, timeout: int):
    return subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=timeout, check=False
    )

def run_code(language, code, stdin=None, timeout_sec=8, mem_limit_mb=256):
    language = (language or "python").lower().strip()
    if language not in LANG_HOST:
        return {"stdout": "", "stderr": f"Unsupported language: {language}", "exit_code": 127}

    if not USE_DOCKER:
        # ---------- Old behavior: run on host ----------
        spec = LANG_HOST[language]
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "main" + spec["ext"])
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            cmd = spec["cmd"].format(file=shlex.quote(path))
            try:
                proc = subprocess.run(
                    cmd, shell=True,
                    input=(stdin.encode() if stdin else None),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=timeout_sec, check=False
                )
                return {
                    "stdout": proc.stdout.decode(),
                    "stderr": proc.stderr.decode(),
                    "exit_code": proc.returncode
                }
            except subprocess.TimeoutExpired:
                return {"stdout": "", "stderr": "Execution timed out", "exit_code": 124}

    # ---------- Docker sandbox (ephemeral container per job) ----------
    img = LANG_IMAGE[language]
    exec_cmd = LANG_CMD_IN_CONTAINER[language]
    file_name = {
        "python": "main.py",
        "javascript": "main.js",
        "r": "main.R",
        "bash": "main.sh",
    }[language]

    try:
        with tempfile.TemporaryDirectory() as td:
            host_file = os.path.join(td, file_name)
            with open(host_file, "w", encoding="utf-8") as f:
                f.write(code)

            limits = f'--memory={mem_limit_mb}m --memory-swap={mem_limit_mb}m --cpus="0.5" --pids-limit=64'
            security = '--security-opt no-new-privileges:true --cap-drop ALL --read-only'
            tmpfs = '--tmpfs /tmp:rw,noexec,nosuid,size=64m --tmpfs /work:rw,noexec,nosuid,size=64m'
            # mount code read-only into /work; container writes to tmpfs /work
            mount = f'-v {shlex.quote(host_file)}:/work/{shlex.quote(file_name)}:ro'

            run = (
                f'docker run --rm --network=none {limits} {security} {tmpfs} '
                f'--workdir /work --user 1000:1000 '
                f'{mount} {shlex.quote(img)} sh -lc {shlex.quote(exec_cmd)}'
            )

            if stdin:
                run = f'printf %s {shlex.quote(stdin)} | ' + run

            proc = _run_shell(run, timeout=timeout_sec)
            return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}

    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Execution timed out", "exit_code": 124}
    except Exception as e:
        return {"stdout": "", "stderr": f"Runner error: {e}", "exit_code": 125}
