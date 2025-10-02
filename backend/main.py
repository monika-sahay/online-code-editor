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
    """
    Execute code in a temp sandbox dir (no nested containers).
    Supports: python, r, javascript, bash, go, julia, cpp, java.
    Uses subprocess with wall-clock timeout and (when available) prlimit caps.
    """
    code = (request.code or "").rstrip()
    if not code:
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    temp_dir = None
    try:
        # 0) Prepare workspace
        temp_dir = tempfile.mkdtemp()
        lang = (request.language or "python").lower().strip()
        supported = {"python", "r", "javascript", "bash", "go", "julia", "cpp", "java"}
        if lang not in supported:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")

        # 1) Determine file name & write user code
        # Java must be Main.java when public class Main is used
        if lang == "java":
            script_path = os.path.join(temp_dir, "Main.java")
        else:
            ext_map = {
                "python": "py",
                "r": "R",
                "javascript": "js",
                "bash": "sh",
                "go": "go",
                "julia": "jl",
                "cpp": "cpp",
                "java": "java",  # unused when lang == java due to special case above
            }
            script_path = os.path.join(temp_dir, f"script.{ext_map[lang]}")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        logger.info(f"Executing {lang} code in temporary file: {script_path}")

        # 2) Build base command (Render-safe, no nested containers)
        prlimit = which("prlimit")  # available if util-linux is installed in the image
        out_bin = os.path.join(temp_dir, "a.out")  # for C++ compiled binary

        base_map = {
            "python": ["python3", script_path],
            "r": ["Rscript", "--vanilla", script_path],
            "javascript": ["node", script_path],
            "bash": ["bash", script_path],
            "go": ["bash", "-lc", f"cd {shlex.quote(temp_dir)} && go run {shlex.quote(script_path)}"],
            "julia": ["julia", script_path],
            "cpp": ["bash", "-lc",
                    f"g++ -O2 {shlex.quote(script_path)} -o {shlex.quote(out_bin)} && {shlex.quote(out_bin)}"],
            # NOTE: user code must declare `public class Main` for Java.
            "java": ["bash", "-lc",
                     f"javac {shlex.quote(script_path)} && java -cp {shlex.quote(temp_dir)} Main"],
        }
        cmd = base_map[lang]

        # 2a) Windows local dev guard for "bash" language (no WSL)
        if os.name == "nt" and lang == "bash":
            return CodeResponse(
                output="",
                error="Bash execution on Windows requires WSL. Run in Docker/WSL or choose another language.",
                success=False,
            )

        # 3) Apply best-effort caps for non-bash top-level commands
        # IMPORTANT: do NOT cap nproc; Node/R need threads/forks. Keep mem + CPU only.
        if prlimit and cmd[0] != "bash":
            cmd = ["prlimit", "--as=268435456", "--cpu=10", "--"] + cmd
            # --as   ≈ 256 MB address space
            # --cpu  10 seconds CPU

        # 4) Execute with wall-clock timeout (longer for compiled langs on cold start)
        timeout_sec = 60 if lang in {"go", "cpp", "java"} else 30
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=temp_dir,
        )

        # 5) Return
        if result.returncode == 0:
            return CodeResponse(output=result.stdout, error=result.stderr, success=True)
        else:
            return CodeResponse(output=result.stdout, error=result.stderr, success=False)

    except subprocess.TimeoutExpired:
        logger.error("Code execution timed out")
        return CodeResponse(output="", error="Code execution timed out", success=False)
    except FileNotFoundError as e:
        # e.g., 'Rscript', 'node', 'julia', 'g++', 'javac' not installed
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
