from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import tempfile
import os
import json
import logging
import sys
import time
from shutil import which
import shlex
import platform
import openai

# --- OpenAI key (for /ai-complete) ---
openai.api_key = os.environ.get("OPENAI_API_KEY")

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Code Execution API", version="1.0.0")

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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class CodeRequest(BaseModel):
    code: str
    language: str = "python"  # "python" | "r" | "javascript" | ...

class CodeResponse(BaseModel):
    output: str
    error: str = ""
    success: bool = True


# --- OS helpers ---
IS_WINDOWS = (os.name == "nt")

def to_bash_path(p: str) -> str:
    """
    Convert a Windows path to POSIX style for Git Bash.
    Uses cygpath if available, else best-effort.
    """
    cp = which("cygpath")
    if cp:
        try:
            out = subprocess.run([cp, "-u", p], capture_output=True, text=True, check=True)
            return out.stdout.strip()
        except Exception:
            pass
    # fallback
    p2 = p.replace("\\", "/")
    if len(p2) >= 2 and p2[1] == ":":
        drive = p2[0].lower()
        p2 = f"/{drive}{p2[2:]}"
    return p2

def cleanup_dir(path: str, logger):
    """Try remove temp dir with retries (Windows can hold locks briefly)."""
    import shutil
    for i in range(6):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
            return
        except Exception:
            time.sleep(0.25 * (i + 1))
    logger.error(f"Failed to clean up temporary directory after retries: {path}")


# --- Routes ---
@app.get("/")
async def root():
    return {"message": "Code Execution API is running"}


# --- Execute code ---
@app.post("/execute", response_model=CodeResponse)
async def execute_code(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        lang = (request.language or "python").lower().strip()
        supported = {"python", "r", "javascript", "bash", "go", "julia", "cpp", "java"}
        if lang not in supported:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")

        # --- filenames ---
        ext_map = {"python":"py","r":"R","javascript":"js","bash":"sh","go":"go","julia":"jl","cpp":"cpp","java":"java"}
        if lang == "java":
            script_path = os.path.join(temp_dir, "Main.java")  # must match public class Main
        else:
            script_path = os.path.join(temp_dir, f"script.{ext_map[lang]}")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(request.code)

        logger.info(f"Executing {lang} code in temporary file: {script_path}")

        # --- commands ---
        prlimit = which("prlimit")
        out_bin = os.path.join(temp_dir, "a.out")

        base_map = {
            "python": ["python3", script_path],
            "r": ["Rscript", "--vanilla", script_path],
            "javascript": ["node", script_path],
            "bash": ["bash", script_path],
            "go": ["bash", "-lc", f"cd {shlex.quote(temp_dir)} && go run {shlex.quote(script_path)}"],
            "julia": ["julia", script_path],
            "cpp": ["bash", "-lc", f"g++ -O2 {shlex.quote(script_path)} -o {shlex.quote(out_bin)} && {shlex.quote(out_bin)}"],
            "java": ["bash", "-lc", f"javac {shlex.quote(script_path)} && java -cp {shlex.quote(temp_dir)} Main"],
        }
        cmd = base_map[lang]

        # --- env tweaks for Node ---
        run_env = None
        if lang == "javascript":
            run_env = os.environ.copy()
            run_env["UV_THREADPOOL_SIZE"] = "2"
            run_env["NODE_OPTIONS"] = "--max-old-space-size=256"

        # --- best-effort caps ---
        # skip for javascript and r; keep for others (slightly higher memory)
        if prlimit and cmd[0] != "bash" and lang not in {"javascript", "r"}:
            cmd = ["prlimit", "--as=536870912", "--cpu=10", "--nproc=512", "--"] + cmd

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=temp_dir,
            env=run_env,
        )

        if result.returncode == 0:
            return CodeResponse(output=result.stdout, error=result.stderr, success=True)
        else:
            return CodeResponse(output=result.stdout, error=result.stderr, success=False)

    except subprocess.TimeoutExpired:
        logger.error("Code execution timed out")
        return CodeResponse(output="", error="Code execution timed out (30 seconds limit)", success=False)
    except FileNotFoundError as e:
        logger.error(f"Runtime not found: {e}")
        return CodeResponse(output="", error=f"Runtime not found: {e}", success=False)
    except Exception as e:
        logger.exception("Unexpected error")
        return CodeResponse(output="", error=f"Unexpected error: {str(e)}", success=False)
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Failed to clean up temporary directory: {e}")



# --- AI completion ---
@app.post("/ai-complete")
async def ai_complete(request: Request):
    data = await request.json()
    code = data.get("code", "")
    cursor_offset = data.get("cursorOffset")  # Optional: can use for context

    if not code.strip():
        return {"suggestion": ""}

    prompt = (
        "You are a coding assistant. Suggest the next line or completion for the following code:\n"
        f"{code}\n# Suggest code completion below:\n"
    )

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
