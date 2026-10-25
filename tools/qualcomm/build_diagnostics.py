"""Compile the same Vulkan tracing source for native Android and glibc/libhybris."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def build(output, ndk, native=False):
    host = 'windows-x86_64' if os.name == 'nt' else 'darwin-x86_64' if os.uname().sysname == 'Darwin' else 'linux-x86_64'
    toolchain = ndk / 'toolchains/llvm/prebuilt' / host
    compiler = toolchain / ('bin/clang.exe' if os.name == 'nt' else 'bin/clang')
    source = Path(__file__).with_name('vulkan_trace.c')
    output.parent.mkdir(parents=True, exist_ok=True)
    arguments = ['--target=aarch64-linux-android26', '-fPIE', '-pie', '-ldl'] if native else [
        '--target=aarch64-linux-gnu', '-nostdlib', '-shared', '-fPIC', '-fno-stack-protector',
        '-DDROIDDECK_VK_TRACE_SHARED', '-D__ANDROID_MIN_SDK_VERSION__=26']
    subprocess.run([str(compiler), '--sysroot=' + str(toolchain / 'sysroot'),
                    '-I' + str(toolchain / 'sysroot/usr/include/aarch64-linux-android'),
                    '-fuse-ld=lld', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-Wl,-z,max-page-size=16384', *arguments, str(source), '-o', str(output)], check=True)
    strip = toolchain / ('bin/llvm-strip.exe' if os.name == 'nt' else 'bin/llvm-strip')
    subprocess.run([str(strip), '--strip-unneeded', str(output)], check=True)
    root = Path(__file__).resolve().parents[2]
    sources = [source, source.with_name('hal_probe_abi.h'), Path(__file__)]
    metadata = dict(schema=1, native=native, binary_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                    sources={path.resolve().relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sources},
                    compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),
                    ndk=(ndk / 'source.properties').read_text())
    output.with_name(output.name + '.build-info').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args()
    build(args.output, args.ndk, args.native)
