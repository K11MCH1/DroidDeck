import ctypes as c
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
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

    def test_trace_cases_are_started_in_disposable_children(self):
        with patch.object(diagnostics.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, b'')) as run, \
             patch('sys.stdout', new_callable=io.StringIO):
            diagnostics.run_case('hal-version', 0, layers=False)
        self.assertEqual(run.call_args.args[0][-3:], ['--trace', 'hal-version', '0'])
        self.assertEqual(run.call_args.kwargs['timeout'], 4)


@unittest.skipUnless(os.environ.get('A850_TRACE_TEST'), 'Set A850_TRACE_TEST to the compiled test_vulkan_trace executable')
class NativeTraceTest(unittest.TestCase):
    def trace(self, mode, result):
        completed = subprocess.run([os.environ['A850_TRACE_TEST'], mode, str(result)],
                                   capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0 if result == 0 else 1, completed.stderr)
        return [json.loads(line) for line in completed.stdout.splitlines()]

    def test_hal_version_positive_failure_and_written_value_are_preserved(self):
        events = self.trace('hal-version', 1)
        version = next(event for event in events if event['event'] == 'version.result')
        self.assertEqual(version['result'], 1)
        self.assertTrue(version['written'])
        self.assertEqual(version['raw'], (1 << 22) | (4 << 12))

    def test_loader_initialization_order_is_recorded(self):
        events = self.trace('hal-version-after-loader', 1)
        versions = [event for event in events if event['event'] == 'version.result']
        self.assertEqual(versions[0]['source'], 'platform.before-hal.version')
        self.assertEqual(versions[0]['result'], 0)
        self.assertEqual(versions[1]['result'], 1)

    def test_failed_creation_does_not_destroy_an_invalid_instance(self):
        events = self.trace('platform', 1)
        result = next(event for event in events if event['event'] == 'instance.result')
        self.assertEqual(result['result'], 1)
        self.assertFalse(any(event['event'] == 'instance.destroyed' for event in events))

    def test_successful_instance_is_destroyed(self):
        events = self.trace('platform', 0)
        self.assertTrue(any(event['event'] == 'instance.destroyed' for event in events))

    def test_function_owner_strings_are_valid_json(self):
        events = self.trace('hal-version', 0)
        function = next(event for event in events if event['event'] == 'function.resolved' and event['owner_found'])
        self.assertEqual(function['module'], 'mock\\module"name\n.so')
        unknown = next(event for event in events if event.get('name') == 'HAL.gipa.unknown-command')
        self.assertFalse(unknown['owner_found'])


class DiagnosticAttestationTest(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'release/runtime_inputs.py'
        spec = importlib.util.spec_from_file_location('a850_runtime_inputs', source)
        self.runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runtime)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        sources = {}
        for name in ('vulkan_trace.c', 'hal_probe_abi.h', 'build_diagnostics.py'):
            path = self.root / 'tools/qualcomm' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
            sources[path.relative_to(self.root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        for relative, native in [('app/build/a850Native/arm64-v8a/liba850vulkanprobe.so', True),
                                 ('app/build/qualcommAssets/qualcomm/shaders/vulkan-trace.so', False)]:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'verified ELF fixture')
            metadata = dict(schema=1, native=native, sources=sources,
                            binary_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            path.with_name(path.name + '.build-info').write_text(json.dumps(metadata))

    def test_both_diagnostic_binaries_are_attested(self):
        expected = self.runtime.diagnostic_assets(self.root)
        self.assertEqual(set(expected), {'lib/arm64-v8a/liba850vulkanprobe.so',
                                         'assets/qualcomm/shaders/vulkan-trace.so'})

    def test_changed_probe_source_invalidates_the_build(self):
        (self.root / 'tools/qualcomm/vulkan_trace.c').write_bytes(b'changed source')
        with self.assertRaisesRegex(ValueError, 'differs from its source'):
            self.runtime.diagnostic_assets(self.root)

    def test_changed_probe_binary_is_rejected(self):
        (self.root / 'app/build/a850Native/arm64-v8a/liba850vulkanprobe.so').write_bytes(b'changed binary')
        with self.assertRaisesRegex(ValueError, 'differs from its source'):
            self.runtime.diagnostic_assets(self.root)


if __name__ == '__main__':
    unittest.main()
