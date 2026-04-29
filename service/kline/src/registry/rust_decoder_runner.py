import json
import os
import subprocess
from pathlib import Path


class RustDecoderRunner:
    def decode(
        self,
        *,
        app_type: str,
        payload_kind: str,
        application_id: str,
        raw_bytes: bytes,
    ) -> dict:
        request = {
            'app_type': str(app_type),
            'payload_kind': str(payload_kind),
            'application_id': str(application_id),
            'raw_bytes_hex': raw_bytes.hex(),
        }
        process = subprocess.run(
            self._command(),
            input=json.dumps(request),
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
            check=False,
        )
        if process.returncode != 0:
            error = process.stderr.strip() or process.stdout.strip() or 'rust decoder failed'
            raise ValueError(error)
        return json.loads(process.stdout)

    def _command(self) -> list[str]:
        configured = os.getenv('KLINE_RUST_DECODER_BIN')
        if configured:
            return [configured]
        return [
            'cargo',
            'run',
            '--quiet',
            '-p',
            'abi',
            '--bin',
            'canonical_decoder',
            '--',
        ]

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[4]
