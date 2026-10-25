import ctypes as c
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'linuxfs/overlay/usr/local/bin/droiddeck-vulkan-diagnostics'
loader = importlib.machinery.SourceFileLoader('a850_diagnostics', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
diagnostics = importlib.util.module_from_spec(spec)
loader.exec_module(diagnostics)


class VulkanDiagnosticsTest(unittest.TestCase):
    def run_probe(self, result, wsi=False, handle=123):
        requests, destroyed = [], []

        def enumerate_extensions(layer, count, extensions):
            c.cast(count, c.POINTER(diagnostics.U))[0] = 0
            return 0

        def create(info_pointer, allocator, instance_pointer):
            info = c.cast(info_pointer, c.POINTER(diagnostics.Instance)).contents
            requests.append(dict(api=info.application.contents.api,
                                 extensions=[info.extensions[i].decode() for i in range(info.extensionCount)],
                                 pnext=info.next, layers=info.layerCount, allocator=allocator))
            c.cast(instance_pointer, c.POINTER(diagnostics.H))[0] = handle
            return result

        functions = {b'vkEnumerateInstanceExtensionProperties': enumerate_extensions,
                     b'vkCreateInstance': create,
                     b'vkDestroyInstance': lambda instance, allocator: destroyed.append(instance.value)}
        with patch.object(diagnostics, 'resolver', return_value=(lambda instance, name: name if name in functions else None, object())), \
             patch.object(diagnostics, 'function', side_effect=lambda address, *args: functions[address]), \
             patch.object(diagnostics, 'mapped_libraries'), patch('sys.stdout', new_callable=io.StringIO):
            status = diagnostics.child('linux', 3, wsi)
        return status, requests, destroyed

    def test_successful_wsi_instance_is_destroyed(self):
        status, requests, destroyed = self.run_probe(0, wsi=True)
        self.assertEqual(status, 0)
        self.assertEqual(destroyed, [123])
        self.assertEqual(requests, [dict(api=(1 << 22) | (3 << 12), extensions=list(diagnostics.WSI),
                                         pnext=None, layers=0, allocator=None)])

    def test_positive_failure_is_preserved_and_handle_is_never_destroyed(self):
        status, requests, destroyed = self.run_probe(1)
        self.assertEqual(status, 1)
        self.assertEqual(requests[0]['extensions'], [])
        self.assertEqual(destroyed, [])

    def test_success_without_a_handle_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'no handle'):
            self.run_probe(0, handle=None)

    def test_timeout_retains_partial_diagnostics(self):
        timeout = subprocess.TimeoutExpired(['probe'], 4, output=b'instance.creating\n')
        with patch.object(diagnostics.subprocess, 'run', side_effect=timeout), \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            diagnostics.run_case('linux', 3)
        self.assertIn('instance.creating', output.getvalue())
        self.assertIn('"status": "timeout"', output.getvalue())

    def test_layer_isolation_changes_only_the_child_environment(self):
        environment = {'VK_INSTANCE_LAYERS': 'diagnostic-layer', 'VK_ICD_FILENAMES': '/same/icd.json'}
        with patch.dict(os.environ, environment, clear=True), \
             patch.object(diagnostics.subprocess, 'run', return_value=subprocess.CompletedProcess([], -11, b'crashed')) as run, \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            diagnostics.run_case('icd', 3, layers=False)
            child_environment = run.call_args.kwargs['env']
            self.assertEqual(os.environ['VK_INSTANCE_LAYERS'], 'diagnostic-layer')
        self.assertNotIn('VK_INSTANCE_LAYERS', child_environment)
        self.assertEqual(child_environment['VK_LOADER_LAYERS_DISABLE'], '~implicit~')
        self.assertEqual(child_environment['VK_ICD_FILENAMES'], '/same/icd.json')
        self.assertIn('"status": -11', output.getvalue())


if __name__ == '__main__':
    unittest.main()
