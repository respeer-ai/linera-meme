import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

