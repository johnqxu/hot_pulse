"""TikHub API 测试脚本 — 测试 fetch_user_post_videos 函数。

用法:
    uv run python test_tikhub.py
    uv run python test_tikhub.py --sec-uid <自定义sec_uid>
    uv run python test_tikhub.py --raw    # 仅发一次原始请求，打印完整响应
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

from hot_pulse.config import load_config
from hot_pulse.tikhub import TikHubClient


def main() -> None:
    parser = argparse.ArgumentParser(description="TikHub API 诊断测试")
    parser.add_argument(
        "--sec-uid",
        help="指定 sec_uid（不指定则用 config.yaml 中所有创作者）",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="原始模式：直接发一次 HTTP 请求，打印完整响应（含请求头和响应体）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  TikHub API 诊断测试")
    print("=" * 60)

    # 1. 加载配置
    print("\n[1] 加载配置...")
    try:
        config = load_config()
    except Exception as e:
        print(f"  ✗ 配置加载失败: {e}")
        sys.exit(1)

    # 2. 诊断 Secrets
    print("\n[2] 密钥诊断...")
    secrets = config.secrets
    if secrets is None:
        print("  ✗ config.secrets 为 None")
        sys.exit(1)

    tk = secrets.tikhub_api_key
    if not tk:
        print("  ✗ TIKHUB_API_KEY 为空")
        sys.exit(1)
    print(f"  ✓ TIKHUB_API_KEY: {tk[:8]}...{tk[-4:]} (长度={len(tk)})")
    print(f"  ✓ BASE_URL: {config.tikhub.base_url}")
    print(f"  ✓ ENDPOINT: {config.tikhub.endpoint}")

    sec_uids = [args.sec_uid] if args.sec_uid else [c.sec_uid for c in config.creators]
    if not sec_uids:
        print("\n  ✗ 无 sec_uid")
        sys.exit(1)

    # 原始模式：手工构造一次请求，打印所有细节
    if args.raw:
        sec_uid = sec_uids[0]
        url = f"{config.tikhub.base_url}{config.tikhub.endpoint}"
        params = {"sec_user_id": sec_uid, "count": config.tikhub.max_count, "max_cursor": 0}
        headers = {"Authorization": f"Bearer {tk}"}

        print(f"\n[RAW] 请求 URL: {url}")
        print(f"[RAW] 参数: {json.dumps(params, indent=2)}")
        print(f"[RAW] Authorization: Bearer {tk[:8]}...{tk[-4:]}")
        print(f"[RAW] 发送中...")

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, params=params, headers=headers)
        except Exception as e:
            print(f"\n  ✗ 网络异常: {e}")
            sys.exit(1)

        print(f"\n[RAW] HTTP 状态码: {resp.status_code}")
        print(f"[RAW] 响应头: {dict(resp.headers)}")
        try:
            body = resp.json()
            print(f"[RAW] JSON 响应体:\n{json.dumps(body, indent=2, ensure_ascii=False)}")
        except Exception:
            print(f"[RAW] 原始响应体 (前2000字符):\n{resp.text[:2000]}")
        sys.exit(0)

    # 正常模式：走 TikHubClient
    print("\n[3] 初始化 TikHubClient...")
    try:
        client = TikHubClient(config)
    except Exception as e:
        print(f"  ✗ 初始化失败: {e}")
        sys.exit(1)
    print("  ✓ 客户端初始化成功")

    for sec_uid in sec_uids:
        name = ""
        for c in config.creators:
            if c.sec_uid == sec_uid:
                name = c.name
                break

        print(f"\n[4] 测试 sec_uid: {sec_uid[:20]}... ({name or '自定义'})")
        print("-" * 40)

        try:
            videos = client.fetch_user_post_videos(sec_uid)
        except httpx.HTTPStatusError as e:
            print(f"  ✗ HTTP 错误: status={e.response.status_code}")
            try:
                body = e.response.json()
                print(f"  ✗ 响应体:\n{json.dumps(body, indent=2, ensure_ascii=False)}")
            except Exception:
                print(f"  ✗ 响应体:\n{e.response.text[:2000]}")
            continue
        except Exception as e:
            print(f"  ✗ 请求失败: {type(e).__name__}: {e}")
            continue

        print(f"  ✓ 成功! 获取到 {len(videos)} 条视频")
        for i, v in enumerate(videos):
            print(f"  [{i+1}] video_id={v.video_id}")
            print(f"       title={v.title[:60] if v.title else '(无标题)'}")
            print(f"       url={v.url[:80] if v.url else '(无URL)'}")
            print(f"       play_urls={len(v.play_urls)} 个")

    client.close()
    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
