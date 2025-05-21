from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from socket import SocketIO

import uuid, docker, logging, tarfile, io, os, tempfile

logger = logging.getLogger("uvicorn.error")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

try:
    CLIENT = docker.from_env()
except docker.errors.DockerException as e:
    logger.error("Docker is not running or not accessible, exiting.")
    raise SystemExit from e


try:
    CLIENT.images.get("python-runner:latest")
    
except docker.errors.ImageNotFound:
    print("Image not found, building...")
    logger.warning("Docker image not found, building...")
    
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

    # Enable network for dependency installation
    container = CLIENT.containers.run(
        "python-runner",
        name=container_id,
        command="tail -f /dev/null",
        detach=True,
        tty=True,
        auto_remove=True,
        network_disabled=False,
        mem_limit="256m",
        pids_limit=64
    )
    
    if request.dependencies:
        pip_cmd = f"source /sandbox/venv/bin/activate && pip install {' '.join(request.dependencies)}"
        
        exec_result = container.exec_run(
            cmd=["/bin/bash", "-c", pip_cmd],
            user="runner"
        )
        
        if exec_result.exit_code != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to install dependencies: {exec_result.output.decode()}"
            )
    
    # Disable network after dependencies are installed
    try:
        CLIENT.api.disconnect_container_from_network(container.id, "bridge")
    except Exception:
        pass
    
    print(request.code)
    
    code_file = "/sandbox/run.py"

    # Write code to a temporary file and copy it into the container
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write(request.code)
        tmp_path = tmp.name

    tar_stream = io.BytesIO()
    
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        tar.add(tmp_path, arcname="run.py")
    tar_stream.seek(0)
    
    container.put_archive("/sandbox", tar_stream.read())
    os.unlink(tmp_path)

    container.exec_run(
        cmd=["/bin/bash", "-c", "chown runner:runner /sandbox/run.py && chmod 644 /sandbox/run.py"],
        user="root"
    )
    
    def stream_output():
        try:
            exec_result = container.exec_run(
                cmd=["/bin/bash", "-c", f"source /sandbox/venv/bin/activate && python {code_file}"],
                user="runner",
                stream=True,
                demux=True
            )
            for stdout, stderr in exec_result.output:
                if stdout:
                    yield stdout
                if stderr:
                    yield stderr
        finally:
            try:
                container.stop(timeout=1)
            except docker.errors.NotFound:
                pass
    
    return StreamingResponse(stream_output(), media_type="application/octet-stream")
