import json
import os
import subprocess


class MockModel:
    def generate(self, prompt: str) -> str:
        if "PLANNING MODE" in prompt:
            return "\n".join(
                ["1. Inspect repository", "2. Run tests", "3. Fix failing module", "4. Re-run tests"]
            )
        if "STEP: Inspect repository" in prompt:
            return json.dumps({"tool": "list_dir", "path": "."})
        if "STEP: Run tests" in prompt:
            return json.dumps({"tool": "shell", "command": "python -m unittest"})
        if "STEP: Fix failing module" in prompt:
            return json.dumps({"tool": "write_file", "path": "calculator.py", "content": "def add(a, b):\n    return a + b\n"})
        if "STEP: Re-run tests" in prompt:
            return json.dumps({"tool": "shell", "command": "python -m unittest"})
        return json.dumps({"tool": "shell", "command": "echo noop"})


class OllamaModel:
    def __init__(self, model: str, timeout: int = 240, endpoint: str = "http://127.0.0.1:11434/api/generate"):
        self.model = model
        self.timeout = timeout
        self.endpoint = endpoint

    def generate(self, prompt: str) -> str:
        planning = "PLANNING MODE" in prompt
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",
                "options": {
                    "temperature": 0,
                    "num_ctx": 2048,
                    "num_predict": 96 if planning else 64,
                },
            }
        )
        proc = subprocess.run(
            [
                "curl",
                "-s",
                self.endpoint,
                "-H",
                "Content-Type: application/json",
                "-d",
                payload,
            ],
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"curl failed with code {proc.returncode}")
        body = json.loads(proc.stdout)
        return body["response"].strip()


def build_model():
    model_name = os.getenv("OLLAMA_MODEL")
    if model_name:
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "240"))
        return OllamaModel(model_name, timeout=timeout)
    return MockModel()
