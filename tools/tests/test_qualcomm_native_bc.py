import ctypes as c
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import patch


PROBE = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                          'linuxfs/overlay/usr/local/bin/droiddeck-qualcomm-native-bc'))['probe']


class NativeBcTest(unittest.TestCase):
    def run_probe(self, missing=None, feature=True, devices=2, enumerate_result=0):
        destroyed = []

        def create(info, allocator, instance):
            c.cast(instance, c.POINTER(c.c_void_p))[0] = 1
            return 0

        def enumerate_devices(instance, count, output):
            c.cast(count, c.POINTER(c.c_uint32))[0] = devices
            if output is not None:
                for i in range(devices):
                    output[i] = i + 2
            return enumerate_result

        def get_features(device, output):
            output[22] = feature

        def get_formats(device, format_id, output):
            output[1] = 0 if (device, format_id) == missing else 1

        def destroy(instance, allocator):
            destroyed.append(instance.value)

        vk = SimpleNamespace(vkCreateInstance=create, vkEnumeratePhysicalDevices=enumerate_devices,
                             vkGetPhysicalDeviceFeatures=get_features, vkGetPhysicalDeviceFormatProperties=get_formats,
                             vkDestroyInstance=destroy)
        with patch.dict('os.environ', HYBRIS_BC_TEXTURES='0'), patch.object(c, 'CDLL', return_value=vk):
            supported = PROBE()
        self.assertEqual(destroyed, [1])
        return supported

    def test_all_devices_and_bc_formats_must_support_native_sampling(self):
        self.assertTrue(self.run_probe())
        for device in (2, 3):
            for format_id in range(131, 147):
                with self.subTest(device=device, format_id=format_id):
                    self.assertFalse(self.run_probe(missing=(device, format_id)))

    def test_missing_feature_empty_device_list_and_enumeration_failure_keep_emulation(self):
        self.assertFalse(self.run_probe(feature=False))
        self.assertFalse(self.run_probe(devices=0))
        self.assertFalse(self.run_probe(enumerate_result=5))

    def test_probe_refuses_to_decide_from_emulated_capabilities(self):
        with patch.dict('os.environ', HYBRIS_BC_TEXTURES='force'), patch.object(c, 'CDLL') as loader:
            self.assertFalse(PROBE())
            loader.assert_not_called()


if __name__ == '__main__':
    unittest.main()
