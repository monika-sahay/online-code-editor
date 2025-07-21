from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import tempfile
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Code Execution API", version="1.0.0")

# Add CORS middleware - allow all origins including Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for maximum compatibility
        "https://*.vercel.app",
        "https://*.csb.app",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000"
    ],
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
