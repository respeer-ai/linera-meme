import json
import os
import subprocess
from pathlib import Path


class RustDecoderRunner:
    DEFAULT_TIMEOUT_SECONDS = 10

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
            timeout=self._timeout_seconds(),
        )
        if process.returncode != 0:
            error = process.stderr.strip() or process.stdout.strip() or 'rust decoder failed'
            raise ValueError(error)
        return json.loads(process.stdout)

    def decode_batch(self, requests: list[dict]) -> list[dict]:
        """Decode multiple payloads in a single subprocess call.

        Each request dict must contain ``app_type``, ``payload_kind``,
        ``application_id``, and ``raw_bytes`` (``bytes``).

        Returns a list of result dicts parallel to the input. Each result
        has ``status`` = ``"ok"`` or ``"error"``. On success the result
        also contains ``payload_type``, ``decoder_version``, and
        ``decoded_payload_json``.
        """
        serializable = []
        for req in requests:
            serializable.append({
                'app_type': str(req['app_type']),
                'payload_kind': str(req['payload_kind']),
                'application_id': str(req['application_id']),
                'raw_bytes_hex': req['raw_bytes'].hex(),
            })
        process = subprocess.run(
            self._command(),
            input=json.dumps(serializable),
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
            check=False,
            timeout=self._timeout_seconds(),
        )
        if process.returncode != 0:
            error = process.stderr.strip() or process.stdout.strip() or 'rust decoder batch failed'
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
            'decoder',
            '--bin',
            'canonical_decoder',
            '--',
        ]

    def _timeout_seconds(self) -> float:
        return float(os.getenv('KLINE_RUST_DECODER_TIMEOUT_SECONDS', self.DEFAULT_TIMEOUT_SECONDS))

    def _repo_root(self) -> Path:
        current = Path(__file__).resolve()
        for candidate in (current.parent, *current.parents):
            if (candidate / 'Cargo.toml').exists() and (candidate / 'service').exists():
                return candidate
        return Path.cwd()
