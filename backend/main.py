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
    Execute code in a temp sandbox dir. Supports: python, r, javascript, bash, go, julia, cpp, java
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()

        lang = (request.language or "python").lower().strip()
        supported = {"python", "r", "javascript", "bash", "go", "julia", "cpp", "java"}
        if lang not in supported:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")

        conf = {
            "python": {"ext": "py",  "cmd": lambda p, d: ["python3", p]},
            "r":      {"ext": "R",   "cmd": lambda p, d: ["Rscript", "--vanilla", p]},
            "javascript": {"ext": "js", "cmd": lambda p, d: ["node", p]},
            "bash":   {"ext": "sh",  "cmd": lambda p, d: ["bash", p]},
            "go":     {"ext": "go",  "cmd": lambda p, d: ["bash", "-lc", f"cd {d} && go run {p}"]},
            "julia":  {"ext": "jl",  "cmd": lambda p, d: ["julia", p]},
            "cpp":    {"ext": "cpp", "cmd": lambda p, d: ["bash", "-lc", f"g++ -O2 {p} -o {d}/a.out && {d}/a.out"]},
            "java":   {"ext": "java","cmd": lambda p, d: ["bash", "-lc", f"javac {p} && java -cp {d} Main"]},
        }

        # 1) Create script file path
        script_path = os.path.join(temp_dir, f"script.{conf[lang]['ext']}")

        # 2) Write user code to disk
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(request.code)

        logger.info(f"Executing {lang} code in temporary file: {script_path}")

        # 3) Run it (all lambdas take (path, temp_dir))
        result = subprocess.run(
            conf[lang]["cmd"](script_path, temp_dir),
            capture_output=True,
            text=True,
            timeout=30,
            cwd=temp_dir,
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
