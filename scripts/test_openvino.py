"""OpenVINO 安装配置与诊断脚本。

检查 Intel OpenVINO 运行环境，测试 faster-whisper 的 OpenVINO 加速支持。
适用于 i7-1165G7 + Iris Xe 集成显卡环境。

用法: python scripts/test_openvino.py
"""

from __future__ import annotations

import os
import subprocess
import sys

# 强制无缓冲输出，避免管道环境下输出延迟
sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]


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
    """安装 openvino (通过 uv)。"""
    print("\n[Step 2] 安装 openvino")
    return _run(
        "uv sync --extra gpu",
        ["uv", "sync", "--extra", "gpu"],
    )


def step3_check_openvino_devices() -> None:
    """列出 OpenVINO 可用设备。"""
    print("\n[Step 3] 检查 OpenVINO 可用设备")
    try:
        from openvino import Core
        core = Core()
        devices = core.available_devices
        print(f"  可用设备: {devices}")
        for dev in devices:
            try:
                name = core.get_property(dev, "FULL_DEVICE_NAME")
                print(f"  - {dev}: {name}")
            except Exception:
                print(f"  - {dev}")
    except Exception as e:
        print(f"  检查失败: {e}")


def step4_check_intel_gpu() -> None:
    """检查 Intel GPU 驱动。"""
    print("\n[Step 4] 检查 Intel GPU")
    import platform
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance -ClassName Win32_VideoController | "
                 "Select-Object Name, DriverVersion, Status | Format-List"],
                capture_output=True, text=True,
            )
            print(result.stdout)
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")
        else:
            # Linux: check via lspci / sysfs
            try:
                result = subprocess.run(
                    ["lspci", "-v"], capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.splitlines():
                    if "VGA" in line or "3D" in line or "Display" in line:
                        print(f"  {line.strip()}")
                if result.returncode != 0:
                    raise FileNotFoundError
            except FileNotFoundError:
                # Fallback: check /sys/class/drm
                import glob
                cards = glob.glob("/sys/class/drm/card*")
                for card in sorted(cards):
                    try:
                        with open(f"{card}/device/vendor") as f:
                            vendor = f.read().strip()
                        with open(f"{card}/device/device") as f:
                            device = f.read().strip()
                        print(f"  {card}: vendor={vendor}, device={device}")
                    except OSError:
                        print(f"  {card}")
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

    # 检查 ctranslate2 支持的设备类型
    try:
        from ctranslate2 import Device
        supported = []
        for attr in dir(Device):
            if not attr.startswith("_"):
                try:
                    val = getattr(Device, attr)
                    if not callable(val) and not isinstance(val, property):
                        supported.append(attr)
                except Exception:
                    pass
        print(f"  支持的设备: {supported if supported else '未知 (检查方式受限)'}")
        if "cpu" in supported:
            print("  - CPU: 支持")
        if "cuda" in supported:
            print("  - CUDA: 支持")
        if "openvino" not in [s.lower() for s in supported]:
            print("  - OpenVINO: ctranslate2 4.x 已移除 OpenVINO 后端，",
                  "faster-whisper 将通过 OpenVINO 模型格式 (.xml) 方式使用")
    except Exception as e:
        print(f"  检查失败: {e}")


def step6_test_faster_whisper_openvino() -> None:
    """测试 faster-whisper 能否使用 OpenVINO 设备。"""
    print("\n[Step 6] 测试 faster-whisper + OpenVINO")
    try:
        from faster_whisper import WhisperModel

        # 显示 HF 配置
        hf_endpoint = os.environ.get("HF_ENDPOINT", "")
        print(f"  HF_ENDPOINT: {hf_endpoint or '(默认: huggingface.co)'}")

        # 检查本地已缓存的模型
        import glob
        hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
        cached_models = []
        for snap_dir in glob.glob(f"{hf_cache}/models--*/snapshots/*/"):
            model_bin = os.path.join(snap_dir, "model.bin")
            if os.path.exists(model_bin):
                # 提取模型名: models--Org--model-name -> Org/model-name
                parts = snap_dir.split("/")
                for p in parts:
                    if p.startswith("models--"):
                        name = p[len("models--"):].replace("--", "/", 1)
                        cached_models.append(name)
                        break
        if cached_models:
            print(f"  本地缓存模型: {cached_models}")

        # 尝试加载模型
        # 注意: ctranslate2 4.x 已移除 OpenVINO 后端（Device 仅含 cpu/cuda），
        # faster-whisper 的 OpenVINO 支持现通过 OpenVINO 原生模型格式 (.xml) 实现
        test_model = "tiny"
        if cached_models:
            # 优先使用已缓存的模型，提取 size 名
            # e.g. "Systran/faster-whisper-medium" -> "medium"
            raw = cached_models[0].split("/")[-1]  # "faster-whisper-medium"
            size = raw.replace("faster-whisper-", "")  # "medium"
            print(f"  本地缓存: {raw} (size={size})")
            test_model = size
        else:
            print(f"  尝试下载 {test_model} 模型 (device=cpu, compute_type=int8)...")

        model = None
        try:
            model = WhisperModel(test_model, device="cpu", compute_type="int8")
            print("  -> CPU 模式可用!")
        except Exception as e:
            print(f"  -> CPU 模型加载失败: {e}")
            err_str = str(e)
            if "Hub" in err_str or "snapshot" in err_str or "connection" in err_str.lower():
                print("  提示: 网络无法访问 HuggingFace，设置 "
                      "HF_ENDPOINT=https://hf-mirror.com 使用国内镜像")
            return

        # OpenVINO 格式测试
        print(f"  尝试加载 OpenVINO 格式 {test_model} 模型 (device=openvino)...")
        try:
            model_ov = WhisperModel(test_model, device="openvino", compute_type="int8")
            print("  -> OpenVINO 模式可用!")
        except Exception as e:
            err_msg = str(e)
            if "Hub" in err_msg or "snapshot" in err_msg or "connection" in err_msg.lower():
                print(f"  -> OpenVINO 模式需要下载额外文件（网络受限）")
            else:
                print(f"  -> OpenVINO 模式不可用: {err_msg[:300]}")
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
