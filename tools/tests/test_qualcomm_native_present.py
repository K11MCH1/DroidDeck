import os
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import Mock, patch


SOURCE = str(Path(__file__).resolve().parents[1] / 'linuxfs/overlay/usr/local/bin/droiddeck-fex')
try:
    import fcntl
except ImportError:
    with patch.dict(sys.modules, fcntl=Mock()):
        FEX = runpy.run_path(SOURCE)
else:
    FEX = runpy.run_path(SOURCE)
GLOBALS = FEX['main'].__globals__
DEFAULT = dict(DISABLE_GAMESCOPE_WSI='1', WSI_X11_FORCE_SHM='1', DROIDDECK_SYSTEM_QUALCOMM='1',
               DROIDDECK_QUALCOMM_ZERO_COPY='1')


class NativePresentTest(unittest.TestCase):
    def test_only_a_passing_qualcomm_probe_enables_game_bypass(self):
        for extra, enabled in (({}, True), ({'DROIDDECK_SYSTEM_QUALCOMM': '0'}, False),
                               ({'DROIDDECK_QUALCOMM_ZERO_COPY': '0'}, False), ({'BL_QUALCOMM_SHM': '1'}, False)):
            with self.subTest(extra=extra):
                original = dict(DEFAULT, **extra)
                result = FEX['game_presentation'](original)
                self.assertEqual('DISABLE_GAMESCOPE_WSI' not in result, enabled)
                self.assertEqual('WSI_X11_FORCE_SHM' not in result, enabled)
                self.assertEqual(original, dict(DEFAULT, **extra))

    def test_per_game_overrides_are_applied_before_choosing_the_path(self):
        for override in (None, '1'):
            def configured(env):
                if override:
                    env['BL_QUALCOMM_SHM'] = override
                return env
            with patch.dict(os.environ, DEFAULT, clear=True), \
                    patch.dict(GLOBALS, game_environment=configured), patch.dict(GLOBALS, launch=lambda *args: args):
                result = FEX['main'](['steam', 'waitforexitandrun', '/game'])
                self.assertEqual('DISABLE_GAMESCOPE_WSI' in result[1], override == '1')

    def test_regular_programs_and_metadata_queries_keep_their_environment(self):
        with patch.dict(os.environ, DEFAULT, clear=True), patch.dict(GLOBALS, launch=lambda *args: args):
            result = FEX['main'](['run', '--', '/browser'])
            self.assertEqual(result[1], DEFAULT)
            self.assertEqual(FEX['main'](['steam', 'getcompatpath', '/game']), 0)


if __name__ == '__main__':
    unittest.main()
