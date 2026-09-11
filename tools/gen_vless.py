#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成可直接导入客户端的 VLESS 节点 + 订阅（edgetunnel + Pages + IPv6 免流）
用法:
  python gen_vless.py                       # 用示例 IPv6 生成，仅演示
  python gen_vless.py --ip 2606:4700:xxx:xxx   # 传入你优选的 IPv6
  python gen_vless.py --top file.txt        # 从优选结果文件读 TopN
"""
import argparse, base64, os, sys

# ⚠️ 由你替换成自己的值（见 docs/部署提示词.md 第 1 节）
HOST = "<你的pages.dev域名>"        # Pages 生产域名（SNI / Host）
UUID = "<你的UUID>"                  # 你的 VLESS 密码
PORT = "443"
NAME = "CF-IPv6"

def node(ip):
    """返回一行 VLESS URI"""
    remark = f"{NAME}-{ip}"
    return (f"vless://{UUID}@{ip}:{PORT}"
            f"?encryption=none&security=tls&sni={HOST}&type=ws&host={HOST}"
            f"&path=%2F%3Fed%3D2560&fp=chrome&alpn=h2,http/1.1#{remark}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", help="单个优选 IPv6 地址")
    ap.add_argument("--ips", help="多行 IPv6(逗号或换行分隔)")
    ap.add_argument("--out", default="subscription.txt")
    args = ap.parse_args()

    ips = []
    if args.ip:
        ips = [args.ip.strip()]
    elif args.ips:
        import re
        ips = [x.strip() for x in re.split(r"[\s,]+", args.ips) if x.strip()]
    else:
        # 演示用占位（非真实可用地址）
        ips = ["2606:4700:2700:0:0:0:0:1111"]

    lines = [node(ip) for ip in ips]
    txt = "\n".join(lines) + "\n"
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(txt)
    b64 = base64.b64encode(txt.encode()).decode()
    outb64 = os.path.splitext(args.out)[0] + "_base64.txt"
    with open(outb64, "w", encoding="utf-8") as f:
        f.write(b64)
    print(f"[OK] 已生成 {len(ips)} 个 VLESS 节点")
    print(f"    明文: {args.out}")
    print(f"    base64: {outb64}")
    for ip in ips[:3]:
        print("  " + node(ip))

if __name__ == "__main__":
    main()