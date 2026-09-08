# import subprocess
# import time
# from dataclasses import dataclass
# from pathlib import Path

# from utils.logger import setup_logger

# logger = setup_logger(__name__)

# @dataclass
# class CommandResult:
#     """Represents the result of an executed external command."""
#     command: str
#     returncode: int
#     stdout: str
#     stderr: str
#     execution_time: float
#     timed_out: bool = False
    
#     @property
#     def success(self) -> bool:
#         """Returns True if the command exited with code 0 and did not time out."""
#         return self.returncode == 0 and not self.timed_out

# def run_command(
#     command: list[str], 
#     cwd: Path | None = None, 
#     timeout: int | None = None
# ) -> CommandResult:
#     """
#     Safely executes an external command and captures its output.
#     """
#     cmd_str = " ".join(command)
#     logger.info(f"Executing command: {cmd_str}")
    
#     if cwd:
#         logger.debug(f"Working directory: {cwd}")

#     start_time = time.perf_counter()

#     try:
#         result = subprocess.run(
#             command,
#             cwd=cwd,
#             capture_output=True,
#             text=True,
#             encoding="utf-8",
#             timeout=timeout,
#             check=False
#         )
#         execution_time = time.perf_counter() - start_time
        
#         # if result.returncode == 0:
#         #     logger.info(f"Command completed successfully in {execution_time:.2f} seconds: {cmd_str}")
#         # else:
#         #     logger.warning(f"Command failed with exit code {result.returncode} in {execution_time:.2f} seconds: {cmd_str}")
#         #     if result.stderr:
#         #         logger.debug(f"Error output: {result.stderr.strip()}")
#         if result.returncode == 0:
#            logger.info(f"Command completed successfully in {execution_time:.2f} seconds: {cmd_str}")
#         else:
#            logger.warning(f"Command failed with exit code {result.returncode} in {execution_time:.2f} seconds: {cmd_str}")

#         print("\n========== STDOUT ==========")
#         print(result.stdout)
#         print("============================")

#         print("\n========== STDERR ==========")
#         print(result.stderr)
#         print("============================")

#     if result.stderr:
#         logger.debug(f"Error output: {result.stderr.strip()}")
                
#         return CommandResult(
#             command=cmd_str,
#             returncode=result.returncode,
#             stdout=result.stdout.strip() if result.stdout else "",
#             stderr=result.stderr.strip() if result.stderr else "",
#             execution_time=execution_time,
#             timed_out=False
#         )

#     except FileNotFoundError:
#         execution_time = time.perf_counter() - start_time
#         error_msg = f"Executable not found for command: {command[0]}"
#         logger.error(error_msg)
        
#         return CommandResult(
#             command=cmd_str,
#             returncode=-1,
#             stdout="",
#             stderr=error_msg,
#             execution_time=execution_time,
#             timed_out=False
#         )

#     except subprocess.TimeoutExpired as e:
#         execution_time = time.perf_counter() - start_time
#         error_msg = f"Command timed out after {timeout} seconds: {cmd_str}"
#         logger.error(error_msg)
        
#         stdout = e.stdout.decode('utf-8', errors='replace') if isinstance(e.stdout, bytes) else str(e.stdout) if e.stdout else ""
#         stderr = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else str(e.stderr) if e.stderr else error_msg
        
#         return CommandResult(
#             command=cmd_str,
#             returncode=-1,
#             stdout=stdout.strip(),
#             stderr=stderr.strip(),
#             execution_time=execution_time,
#             timed_out=True
#         )

#     except OSError as e:
#         execution_time = time.perf_counter() - start_time
#         error_msg = f"OS error executing command {cmd_str}: {e}"
#         logger.error(error_msg)
        
#         return CommandResult(
#             command=cmd_str,
#             returncode=-1,
#             stdout="",
#             stderr=error_msg,
#             execution_time=execution_time,
#             timed_out=False
#         )
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class CommandResult:
    """Represents the result of an executed external command."""
    command: str
    returncode: int
    stdout: str
    stderr: str
    execution_time: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Returns True if the command exited with code 0 and did not time out."""
        return self.returncode == 0 and not self.timed_out


def run_command(
    command: list[str],
    cwd: Path | None = None,
    timeout: int | None = None,
) -> CommandResult:
    """
    Safely executes an external command and captures its output.
    """
    cmd_str = " ".join(command)
    logger.info(f"Executing command: {cmd_str}")

    if cwd:
        logger.debug(f"Working directory: {cwd}")

    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )

        execution_time = time.perf_counter() - start_time

        if result.returncode == 0:
            logger.info(
                f"Command completed successfully in {execution_time:.2f} seconds: {cmd_str}"
            )
        else:
            logger.warning(
                f"Command failed with exit code {result.returncode} "
                f"in {execution_time:.2f} seconds: {cmd_str}"
            )

        # ====================================================
        # DEBUG OUTPUT (Remove after debugging is complete)
        # ====================================================
        print("\n========== COMMAND ==========")
        print(command)

        print("\n========== RETURN CODE ==========")
        print(result.returncode)

        print("\n========== STDOUT ==========")
        print(result.stdout)

        print("\n========== STDERR ==========")
        print(result.stderr)

        print("\n========== END ==========")
        # ====================================================

        if result.stderr:
            logger.debug(result.stderr.strip())

        return CommandResult(
            command=cmd_str,
            returncode=result.returncode,
            stdout=result.stdout.strip() if result.stdout else "",
            stderr=result.stderr.strip() if result.stderr else "",
            execution_time=execution_time,
            timed_out=False,
        )

    except FileNotFoundError:
        execution_time = time.perf_counter() - start_time
        error_msg = f"Executable not found for command: {command[0]}"
        logger.error(error_msg)

        return CommandResult(
            command=cmd_str,
            returncode=-1,
            stdout="",
            stderr=error_msg,
            execution_time=execution_time,
            timed_out=False,
        )

    except subprocess.TimeoutExpired as e:
        execution_time = time.perf_counter() - start_time
        error_msg = f"Command timed out after {timeout} seconds: {cmd_str}"
        logger.error(error_msg)

        stdout = (
            e.stdout.decode("utf-8", errors="replace")
            if isinstance(e.stdout, bytes)
            else (e.stdout or "")
        )

        stderr = (
            e.stderr.decode("utf-8", errors="replace")
            if isinstance(e.stderr, bytes)
            else (e.stderr or error_msg)
        )

        return CommandResult(
            command=cmd_str,
            returncode=-1,
            stdout=stdout.strip(),
            stderr=stderr.strip(),
            execution_time=execution_time,
            timed_out=True,
        )

    except OSError as e:
        execution_time = time.perf_counter() - start_time
        error_msg = f"OS error executing command {cmd_str}: {e}"
        logger.error(error_msg)

        return CommandResult(
            command=cmd_str,
            returncode=-1,
            stdout="",
            stderr=error_msg,
            execution_time=execution_time,
            timed_out=False,
        )