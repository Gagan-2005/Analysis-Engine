import pytest
from unittest.mock import patch, MagicMock
from utils.docker_runner import run_container

def test_docker_cleanup_on_success():
    with patch("utils.docker_runner.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="output", stderr="")
        run_container("my_image", command=["test"])
        
        # Verify --rm is included to guarantee automatic cleanup
        called_cmd = mock_run.call_args[1]["command"]
        assert "docker" in called_cmd
        assert "run" in called_cmd
        assert "--rm" in called_cmd

def test_docker_cleanup_on_failure():
    with patch("utils.docker_runner.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=False, stdout="", stderr="error")
        run_container("my_image", command=["test"])
        
        called_cmd = mock_run.call_args[1]["command"]
        assert "--rm" in called_cmd

def test_docker_cleanup_on_exception():
    with patch("utils.docker_runner.run_command") as mock_run:
        mock_run.side_effect = Exception("Crash")
        with pytest.raises(Exception):
            run_container("my_image", command=["test"])
            
        called_cmd = mock_run.call_args[1]["command"]
        assert "--rm" in called_cmd

def test_protection_against_deleting_unrelated_containers():
    # Because we use 'docker run --rm', the Docker daemon itself
    # is responsible for deleting ONLY the container created by that command.
    # We do not use 'docker system prune' or 'docker rm' which could
    # target unrelated containers.
    with patch("utils.docker_runner.run_command") as mock_run:
        run_container("my_image")
        called_cmd = mock_run.call_args[1]["command"]
        assert "prune" not in called_cmd
        assert "rm" not in called_cmd  # 'rm' is not used directly, '--rm' is.
