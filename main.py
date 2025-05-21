from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import uuid, docker


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

try:
    CLIENT = docker.from_env()
except docker.errors.DockerException as e:
    raise Exception("Docker is not running or not accessible.") from e


try:
    CLIENT.images.get("python-runner:latest")
except docker.errors.ImageNotFound:
    print("Image not found, building...")
    CLIENT.images.build(
        path=".",
        dockerfile="python-runner.dockerfile",
        tag="python-runner"
    )


class CodeRequest(BaseModel):
    code: str
    dependencies: list[str] = []


@app.get("/")
def root():
    return FileResponse("templates/index.html")

    
@app.post("/run")
def run(request: CodeRequest):
    container_id = f"py-sandobxox-{uuid.uuid4().hex[:8]}"
    
    # assert container_id not in containers
    
    try: 
        container = CLIENT.containers.run(
            "python-runner",
            name = container_id,
            command = "tail -f /dev/null",
            detach = True,
            tty = True,
            auto_remove = True,
            network_disabled = True,
            mem_limit = "256m",
            pids_limit = 64
        )
        
        if request.dependencies:
            pip_cmd = f"source /sandbox/venv/bin/activate && pip install {' '.join(request.dependencies)}"
                
            exec_result = container.exec_run(
                cmd = ["/bin/bash", "-c", pip_cmd],
                user = "runner"
            )
            
            if exec_result.exit_code != 0:
                raise HTTPException(
                    status_code = 500,
                    detail = f"Failed to install dependencies: {exec_result.output.decode()}"
                )
        
        code_file = "/sandbox/run.py"
        
        exec_result = container.exec_run(
            cmd = ["/bin/bash", "-c", f"echo {repr(request.code)} > {code_file}"],
            user = "runner",
            stream = True 
        )
        
        exec_result = container.exec_run(
            cmd = ["/bin/bash", "-c", f"source /sandbox/venv/bin/activate && python {code_file}"],
            user = "runner",
        )
        
        output = exec_result.output.decode()
        return {"output": output}
    
    finally:
        try:
            container.stop(timeout=1)
        except docker.errors.NotFound:
            pass