"""OpenVINO 安装配置与诊断脚本。

检查 Intel OpenVINO 运行环境，测试 faster-whisper 的 OpenVINO 加速支持。
适用于 i7-1165G7 + Iris Xe 集成显卡环境。

用法: python scripts/test_openvino.py
"""

from __future__ import annotations

import subprocess
import sys


def _run(desc: str, cmd: list[str]) -> bool:
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"  命令: {' '.join(cmd)}")
    print(f"{'='*60}")
    result = subprocess.run(cmd)
    ok = result.returncode == 0
    print(f"  -> {'通过' if ok else '失败'} (exit code: {result.returncode})")
    return ok


def step1_check_openvino() -> bool:
    """检查 openvino 是否已安装。"""
    print("\n[Step 1] 检查 openvino 包")
    try:
        import openvino
        print(f"  openvino 版本: {openvino.__version__}")
        return True
    except ImportError:
        print("  openvino 未安装")
        return False


def step2_install_openvino() -> bool:
    """安装 openvino。"""
    print("\n[Step 2] 安装 openvino")
    return _run(
        "pip install openvino -i https://mirrors.aliyun.com/pypi/simple/",
        [sys.executable, "-m", "pip", "install", "openvino", "-i", "https://mirrors.aliyun.com/pypi/simple/"],
    )


def step3_check_openvino_devices() -> None:
    """列出 OpenVINO 可用设备。"""
    print("\n[Step 3] 检查 OpenVINO 可用设备")
    try:
        from openvino.runtime import Core
        core = Core()
        devices = core.available_devices
        print(f"  可用设备: {devices}")
        for dev in devices:
            name = core.get_property(dev, "FULL_DEVICE_NAME")
            print(f"  - {dev}: {name}")
    except Exception as e:
        print(f"  检查失败: {e}")


def step4_check_intel_gpu() -> None:
    """检查 Intel GPU 驱动。"""
    print("\n[Step 4] 检查 Intel GPU")
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance -ClassName Win32_VideoController | "
             "Select-Object Name, DriverVersion, Status | Format-List"],
            capture_output=True, text=True,
        )
        print(result.stdout)
        if result.stderr:
            print(f"  stderr: {result.stderr[:500]}")
    except Exception as e:
        print(f"  检查失败: {e}")


def step5_check_ctranslate2_backends() -> None:
    """检查 ctranslate2 支持的后端。"""
    print("\n[Step 5] 检查 ctranslate2 版本与后端")
    try:
        import ctranslate2
        print(f"  ctranslate2 版本: {ctranslate2.__version__}")
    except ImportError:
        print("  ctranslate2 未安装")
        return

    # 尝试创建一个简单的 ctranslate2 设备
    try:
        import ctranslate2
        # 检查 openvino 设备是否被 ctranslate2 识别
        print("  测试 ctranslate2 设备支持...")
        from ctranslate2 import StorageView
        # 尝试在 openvino 设备上创建 tensor
        try:
            t = StorageView.zeros((1, 1), device="openvino")
            print("  openvino 设备: 支持")
        except Exception as e:
            print(f"  openvino 设备: 不支持 ({e})")
    except Exception as e:
        print(f"  测试失败: {e}")


def step6_test_faster_whisper_openvino() -> None:
    """测试 faster-whisper 能否使用 OpenVINO 设备。"""
    print("\n[Step 6] 测试 faster-whisper + OpenVINO")
    try:
        from faster_whisper import WhisperModel

        # 使用 tiny 模型快速测试（很小，下载快）
        print("  尝试加载 tiny 模型 (device=openvino)...")
        try:
            import os
            if not os.environ.get("HF_ENDPOINT"):
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

            model = WhisperModel("tiny", device="openvino", compute_type="int8")
            print("  -> OpenVINO 加速可用!")
        except Exception as e:
            print(f"  -> OpenVINO 不可用: {e}")
            print("  尝试 CPU 模式...")
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            print("  -> CPU 模式可用")
    except Exception as e:
        print(f"  测试失败: {e}")


def main() -> None:
    print("OpenVINO 环境诊断脚本")
    print(f"Python: {sys.version}")
    print(f"平台: {sys.platform}")

    # Step 1: 检查 openvino 是否安装
    has_ov = step1_check_openvino()

    # Step 2: 如果未安装，尝试安装
    if not has_ov:
        ok = step2_install_openvino()
        if ok:
            print("  openvino 安装成功，重新检查...")
            has_ov = step1_check_openvino()

    if not has_ov:
        print("\n  openvino 安装失败，跳过后续 OpenVINO 检查")
        return

    # Step 3-6: 逐步诊断
    step3_check_openvino_devices()
    step4_check_intel_gpu()
    step5_check_ctranslate2_backends()
    step6_test_faster_whisper_openvino()

    print("\n" + "=" * 60)
    print("  诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
