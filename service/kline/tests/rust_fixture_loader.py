import json
import subprocess
from pathlib import Path


class RustFixtureLoader:
    def load_hex(self, fixture_name: str) -> str:
        process = subprocess.run(
            [
                'cargo',
                'run',
                '--quiet',
                '-p',
                'decoder',
                '--bin',
                'test_payload_fixture',
                '--',
                str(fixture_name),
            ],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
            check=False,
        )
        if process.returncode != 0:
            error = process.stderr.strip() or process.stdout.strip() or 'rust fixture failed'
            raise RuntimeError(error)
        payload = json.loads(process.stdout)
        return str(payload['raw_bytes_hex'])

    def load_bytes(self, fixture_name: str) -> bytes:
        return bytes.fromhex(self.load_hex(fixture_name))

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]
