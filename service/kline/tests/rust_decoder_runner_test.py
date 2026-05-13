import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from registry.rust_decoder_runner import RustDecoderRunner


class RustDecoderRunnerTest(unittest.TestCase):
    def test_repo_root_finds_nearest_project_root_without_fixed_depth(self):
        runner = RustDecoderRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / 'Cargo.toml').write_text('', encoding='ascii')
            (root / 'service').mkdir()
            nested = root / 'kline' / 'src' / 'registry' / 'rust_decoder_runner.py'
            nested.parent.mkdir(parents=True)
            nested.write_text('', encoding='ascii')
            with patch('registry.rust_decoder_runner.Path.resolve', return_value=nested):
                self.assertEqual(runner._repo_root(), root)

    def test_decode_passes_timeout_to_subprocess(self):
        runner = RustDecoderRunner()
        completed = Mock(returncode=0, stdout='{}', stderr='')

        with patch('registry.rust_decoder_runner.subprocess.run', return_value=completed) as run_mock:
            with patch.object(runner, '_command', return_value=['decoder']):
                with patch.object(runner, '_repo_root', return_value=Path('/tmp')):
                    with patch.dict('os.environ', {'KLINE_RUST_DECODER_TIMEOUT_SECONDS': '7'}):
                        self.assertEqual(
                            runner.decode(
                                app_type='pool',
                                payload_kind='message',
                                application_id='app',
                                raw_bytes=b'\x01',
                            ),
                            {},
                        )

        self.assertEqual(run_mock.call_args.kwargs['timeout'], 7.0)

    def test_decode_batch_passes_timeout_to_subprocess(self):
        runner = RustDecoderRunner()
        completed = Mock(returncode=0, stdout='[]', stderr='')

        with patch('registry.rust_decoder_runner.subprocess.run', return_value=completed) as run_mock:
            with patch.object(runner, '_command', return_value=['decoder']):
                with patch.object(runner, '_repo_root', return_value=Path('/tmp')):
                    runner.decode_batch([
                        {
                            'app_type': 'pool',
                            'payload_kind': 'message',
                            'application_id': 'app',
                            'raw_bytes': b'\x01',
                        }
                    ])

        self.assertEqual(run_mock.call_args.kwargs['timeout'], runner.DEFAULT_TIMEOUT_SECONDS)
