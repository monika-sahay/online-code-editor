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
    Execute Python code in a Docker container for sandboxing (with fallback to direct execution)
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty")
    
    # Create a temporary file to store the code
    temp_dir = None
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        script_path = os.path.join(temp_dir, "script.py")
        
        # Write code to temporary file
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(request.code)
        
        logger.info(f"Executing code in temporary file: {script_path}")
        
        # Use direct Python execution (Docker not available in this environment)
        try:
            result = subprocess.run(
                ["python3", script_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=temp_dir
            )
            
            if result.returncode == 0:
                return CodeResponse(
                    output=result.stdout,
                    error=result.stderr,
                    success=True
                )
            else:
                return CodeResponse(
                    output=result.stdout,
                    error=result.stderr,
                    success=False
                )
                
        except subprocess.TimeoutExpired:
            logger.error("Code execution timed out")
            return CodeResponse(
                output="",
                error="Code execution timed out (30 seconds limit)",
                success=False
            )
        except FileNotFoundError:
            logger.error("Python3 not found")
            return CodeResponse(
                output="",
                error="Python3 not found. Please ensure Python is installed.",
                success=False
            )
            
    except subprocess.TimeoutExpired:
        logger.error("Code execution timed out")
        return CodeResponse(
            output="",
            error="Code execution timed out (30 seconds limit)",
            success=False
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return CodeResponse(
            output="",
            error=f"Unexpected error: {str(e)}",
            success=False
        )
    finally:
        # Clean up temporary files
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
    response = openai.ChatCompletion.create(
        model="gpt-4o",  # or "gpt-3.5-turbo" for cheaper
        messages=[
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=48,
        temperature=0.2
    )

    # Extract the suggestion from the AI's response
    suggestion = response.choices[0].message.content.strip()

    return {"suggestion": suggestion}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
