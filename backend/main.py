from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import subprocess, tempfile, os, json, logging, sys, time, shlex
from shutil import which
import platform

# --- OpenAI (for /ai-complete) ---
import openai
openai.api_key = os.environ.get("OPENAI_API_KEY")

# --- Queue stack (NEW) ---
from redis import Redis
from rq import Queue
from rq.job import Job

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Code Execution API", version="2.0.0")

# ---------- CORS ----------
origins = [
    "https://online-code-editor-nine-chi.vercel.app",
    "https://*.vercel.app",
    "https://*.onrender.com",
    "https://freeonlineeditor.co.uk",
    "https://www.freeonlineeditor.co.uk",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Helpers ----------
IS_WINDOWS = (os.name == "nt")

def to_bash_path(p: str) -> str:
    cp = which("cygpath")
    if cp:
        try:
            out = subprocess.run([cp, "-u", p], capture_output=True, text=True, check=True)
            return out.stdout.strip()
        except Exception:
            pass
    p2 = p.replace("\\", "/")
    if len(p2) >= 2 and p2[1] == ":":
        drive = p2[0].lower()
        p2 = f"/{drive}{p2[2:]}"
    return p2

# ---------- Models ----------
class CodeRequest(BaseModel):
    code: str
    language: str = "python"

class CodeResponse(BaseModel):
    output: str
    error: str = ""
    success: bool = True

# ======== QUEUE MODE: API + Worker contract ========

# 1) Redis connection (works in Docker Compose and in cloud)
def get_redis():
    # Prefer REDIS_URL if provided by cloud host; else use local service name "redis"
    url = os.getenv("REDIS_URL")
    if url:
        return Redis.from_url(url)
    return Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", "6379")), db=0)

r = get_redis()
q = Queue(os.getenv("RQ_QUEUE", "exec"), connection=r)

class ExecRequest(BaseModel):
    language: str = Field(..., pattern="^(python|javascript|r|bash|go|julia|cpp|java|c|csharp)$")
    code: str
    stdin: str | None = None
    timeout_sec: int = 8
    mem_limit_mb: int = 256

# Import after definition to avoid circulars if runner imports settings
from runner import run_code  # <- your sandboxed executor (next section)

@app.post("/submit", status_code=202)
def submit(req: ExecRequest):
    """
    Enqueue a code-execution job. Returns job_id immediately.
    """
    job = q.enqueue(
        run_code,
        req.language,
        req.code,
        req.stdin,
        req.timeout_sec,
        req.mem_limit_mb,
        job_timeout=req.timeout_sec + 2,   # worker-level hard cap
        failure_ttl=3600,
        result_ttl=3600
    )
    return {"job_id": job.id}

@app.get("/status/{job_id}")
def status(job_id: str):
    job = Job.fetch(job_id, connection=r)
    return {
        "state": job.get_status(),                 # queued | started | finished | failed | canceled
        "enqueued_at": job.enqueued_at,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
        "meta": job.meta or {}
    }

@app.get("/result/{job_id}")
def result(job_id: str):
    job = Job.fetch(job_id, connection=r)
    if job.get_status() == "failed":
        err = str(job.exc_info or "Execution failed")
        raise HTTPException(500, detail={"state": "failed", "error": err})
    if not job.is_finished:
        # 425 Too Early – client should poll again
        raise HTTPException(425, detail={"state": job.get_status()})
    return job.result

@app.post("/cancel/{job_id}")
def cancel(job_id: str):
    job = Job.fetch(job_id, connection=r)
    job.cancel()
    return {"state": "canceled"}

# ======== (Optional) keep your synchronous /execute while you migrate ========

@app.post("/execute", response_model=CodeResponse)
async def execute_code(request: CodeRequest):
    """
    Legacy sync route. You can remove this once the frontend switches to /submit/status/result.
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        lang = (request.language or "python").lower().strip()
        supported = {"python", "r", "javascript", "bash", "go", "julia", "cpp", "java", "c", "csharp"}
        if lang not in supported:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")

        ext_map = {
            "python": "py", "r": "R", "javascript": "js", "bash": "sh",
            "go": "go", "julia": "jl", "cpp": "cpp", "java": "java",
            "c": "c", "csharp": "cs",
        }
        filename = "Main.java" if lang == "java" else f"script.{ext_map[lang]}"
        script_path = os.path.join(temp_dir, filename)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(request.code)

        prlimit = which("prlimit")
        out_bin = os.path.join(temp_dir, "a.out")
        exe_path = os.path.join(temp_dir, "script.exe")  # mono

        if IS_WINDOWS:
            base_map = {
                "python": ["python", script_path],
                "r": ["Rscript", "--vanilla", script_path],
                "javascript": ["node", "--jitless", "--stack_size=512", "--max-old-space-size=64", script_path],
                "bash": ["bash", to_bash_path(script_path)],
                "go": ["go", "run", script_path],
                "julia": ["julia", "--startup-file=no", "--compile=min", "-O0", script_path],
                "cpp": ["cmd", "/c", f"g++ -O2 {script_path} -o {out_bin} && {out_bin}"],
                "java": ["cmd", "/c", f"javac {script_path} && java -cp {temp_dir} Main"],
                "c": ["cmd", "/c", f"gcc -O2 {script_path} -o {out_bin} && {out_bin}"],
                "csharp": ["cmd", "/c", f"mcs {script_path} -out:{exe_path} && mono {exe_path}"],
            }
        else:
            base_map = {
                "python": ["python3", script_path],
                "r": ["Rscript", "--vanilla", script_path],
                "javascript": ["node", "--jitless", "--stack_size=512", "--max-old-space-size=64", script_path],
                "bash": ["bash", script_path],
                "go": ["bash", "-lc", f"set -euo pipefail; cd {shlex.quote(temp_dir)}; go run {shlex.quote(script_path)}"],
                "julia": ["julia", "--startup-file=no", "--compile=min", "-O0", script_path],
                "cpp": ["bash", "-lc", f"g++ -O2 {shlex.quote(script_path)} -o {shlex.quote(out_bin)} && {shlex.quote(out_bin)}"],
                "java": ["bash", "-lc", f"javac {shlex.quote(script_path)} && java -cp {shlex.quote(temp_dir)} Main"],
                "c": ["bash", "-lc", f"gcc -O2 {shlex.quote(script_path)} -o {shlex.quote(out_bin)} && {shlex.quote(out_bin)}"],
                "csharp": ["bash", "-lc", f"mcs {shlex.quote(script_path)} -out:{shlex.quote(exe_path)} && mono {shlex.quote(exe_path)}"],
            }

        cmd = base_map[lang]

        # runtime checks (examples)
        if lang == "r" and which("Rscript") is None:
            return CodeResponse(output="", error="Rscript runtime not installed on server", success=False)
        if lang == "javascript" and which("node") is None:
            return CodeResponse(output="", error="Node.js runtime not installed on server", success=False)

        if which("prlimit") and cmd[0] != "bash" and lang not in {"javascript", "julia", "go", "r"}:
            cmd = ["prlimit", "--as=268435456", "--cpu=10", "--nproc=256", "--"] + cmd

        env = os.environ.copy()
        if lang == "julia":
            env.setdefault("JULIA_NUM_THREADS", "1")

        timeout = 30
        if lang in {"go", "julia", "java", "cpp"}:
            timeout = 120

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=temp_dir, env=env)

        if IS_WINDOWS and lang in {"cpp", "java"} and result.returncode == 0:
            # already handled in command; fallthrough returns compilation step logs
            pass

        if result.returncode == 0:
            return CodeResponse(output=result.stdout, error=result.stderr, success=True)
        else:
            return CodeResponse(output=result.stdout, error=result.stderr, success=False)

    except subprocess.TimeoutExpired:
        logger.error("Code execution timed out")
        return CodeResponse(output="", error="Code execution timed out", success=False)
    except FileNotFoundError as e:
        logger.error(f"Runtime not found: {e}")
        return CodeResponse(output="", error=f"Runtime not found: {e}", success=False)
    except Exception as e:
        logger.exception("Unexpected error")
        return CodeResponse(output="", error=f"Unexpected error: {str(e)}", success=False)
    finally:
        try:
            if temp_dir and os.path.exists(temp_dir):
                import shutil; shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Failed to clean up temporary directory: {e}")

# ---------- Health ----------
@app.get("/")
async def root():
    return {"message": "Code Execution API (queue-enabled) running"}

# ---------- AI completion (unchanged) ----------
@app.post("/ai-complete")
async def ai_complete(request: Request):
    data = await request.json()
    code = data.get("code", "")
    if not code.strip():
        return {"suggestion": ""}

    prompt = ("You are a coding assistant. Suggest the next line or completion for the following code:\n"
              f"{code}\n# Suggest code completion below:\n")

    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=48,
        temperature=0.2
    )
    suggestion = response.choices[0].message.content.strip()
    return {"suggestion": suggestion}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
