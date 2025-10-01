from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import tempfile
import os
import json
import logging
from fastapi import Request
import os
import openai
from shutil import which
import shlex

openai.api_key = os.environ.get("OPENAI_API_KEY")
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Code Execution API", version="1.0.0")
origins = [
    "https://online-code-editor-nine-chi.vercel.app", 
    "https://*.vercel.app",                             # optional wildcard
    "https://*.onrender.com", 
    "https://freeonlineeditor.co.uk",
    "https://www.freeonlineeditor.co.uk",                          # allow Render backend
    "http://localhost:8000",                            # local frontend
    "http://localhost:3000",                            # local frontend alt
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000"
]

# Add CORS middleware - allow all origins including Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str
    language: str = "python"   # "python" | "r"

class CodeResponse(BaseModel):
    output: str
    error: str = ""
    success: bool = True

@app.get("/")
async def root():
    return {"message": "Code Execution API is running"}


@app.post("/execute", response_model=CodeResponse)
async def execute_code(request: CodeRequest):
    """
    Execute code in a temp sandbox dir.
    Supports: python, r, javascript, bash, go, julia, cpp, java
    Uses subprocess with timeout and (when available) prlimit caps.
    """
    if not request.code.strip():
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
        ext_map = {
            "python": "py",
            "r": "R",
            "javascript": "js",
            "bash": "sh",
            "go": "go",
            "julia": "jl",
            "cpp": "cpp",
            "java": "java",
        }
        script_path = os.path.join(temp_dir, f"script.{ext_map[lang]}")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(request.code)

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

        # 3) Apply best-effort caps for non-bash top-level commands
        # (bash -lc already wraps a mini shell pipeline, so prlimit before bash would not apply to the children)
        if prlimit and cmd[0] != "bash":
            cmd = ["prlimit", "--as=268435456", "--cpu=10", "--nproc=256", "--"] + cmd
            # --as   ≈ 256 MB address space cap
            # --cpu  10 seconds CPU time
            # --nproc limit number of processes to curb forks

        # 4) Execute with wall-clock timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,      # wall-clock timeout
            cwd=temp_dir,
        )

        # 5) Return
        if result.returncode == 0:
            return CodeResponse(output=result.stdout, error=result.stderr, success=True)
        else:
            return CodeResponse(output=result.stdout, error=result.stderr, success=False)

    except subprocess.TimeoutExpired:
        logger.error("Code execution timed out")
        return CodeResponse(output="", error="Code execution timed out (30 seconds limit)", success=False)
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



@app.post("/ai-complete")
async def ai_complete(request: Request):
    """
    Given the code and (optional) cursor position, return an AI suggestion/completion.
    """
    data = await request.json()
    code = data.get("code", "")
    cursor_offset = data.get("cursorOffset")  # Optional: can use for context

    if not code.strip():
        return {"suggestion": ""}

    # Build a prompt for the AI model
    prompt = (
        "You are a coding assistant. Suggest the next line or completion for the following code:\n"
        f"{code}\n# Suggest code completion below:\n"
    )

    # Call OpenAI ChatCompletion API
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",   # or "gpt-3.5-turbo-instruct-0914"
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
