from pathlib import Path

from utils.command_runner import run_command, CommandResult
from utils.logger import setup_logger

logger = setup_logger(__name__)


def run_container(
    image: str,
    workdir: str | None = None,
    mounts: list[tuple[Path | str, str]] | None = None,
    command: list[str] | None = None,
    cwd: Path | None = None,
) -> CommandResult:
    """
    Executes a Docker container with standard mapping and execution settings.
    
    Args:
        image: The Docker image tag to run.
        workdir: Optional working directory inside the container.
        mounts: List of (host_path, container_path) tuples to mount as volumes.
        command: Optional command and arguments to pass to the container entrypoint.
        cwd: The working directory for the subprocess on the host.
        
    Returns:
        CommandResult containing success status, stdout, and stderr.
    """
    docker_cmd = ["docker", "run", "--rm"]
    
    if mounts:
        for host_path, container_path in mounts:
            docker_cmd.extend(["-v", f"{host_path}:{container_path}"])
            
    if workdir:
        docker_cmd.extend(["-w", workdir])
        
    docker_cmd.append(image)
    
    if command:
        docker_cmd.extend(command)
        
    logger.debug("Executing Docker container: %s", " ".join(docker_cmd))

    print("\n========== DOCKER COMMAND ==========")
    for i, arg in enumerate(docker_cmd):
     print(f"{i}: {repr(arg)}")
    print("====================================")
    
    result = run_command(command=docker_cmd, cwd=cwd)
    
    if not result.success and result.stderr:
        stderr_lower = result.stderr.lower()
        # Common phrases Docker uses when an image is missing or cannot be pulled
        if any(phrase in stderr_lower for phrase in [
            "pull access denied", 
            "not exist", 
            "not found", 
            "manifest for"
        ]):
            result.stderr = (
                f"Reason:\nDocker image '{image}' was not found.\n\n"
                f"Suggestion:\nUpdate docker_image in config.yaml"
            )
            
    return result
