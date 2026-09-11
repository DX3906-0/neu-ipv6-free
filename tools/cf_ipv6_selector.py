#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare IPv6 优选节点扫描器 —— 纯 Python，零第三方依赖

用途：挑出「你当前网络」到 Cloudflare 边缘最快的 IPv6 节点。
免流场景：把最优节点填进客户端配置的 address 字段（替换域名解析出的默认 IP）。

用法:
  python cf_ipv6_selector.py                # 延迟扫描（默认每段 3 个候选）
  python cf_ipv6_selector.py -n 5           # 每段采 5 个候选
  python cf_ipv6_selector.py -d             # 额外对 Top5 做下载测速
  python cf_ipv6_selector.py -d -b 1000000  # 下载测速每节点 1MB
  python cf_ipv6_selector.py -f ips.txt     # 从文件读候选（每行一个 IP 或 CIDR）
  python cf_ipv6_selector.py -t 2           # TCP 超时 2 秒

重要：校园网免流场景下，请在「校园网 IPv6」环境里运行本脚本，
      因为热点与校园网到 CF 的路由不同，优选结果也会不同。
"""
import argparse
import ipaddress
import random
import socket
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Cloudflare 常用 IPv6 段（社区优选库常用来源）
CF_SEGMENTS = [
    "2606:4700::/48",
    "2606:4700:d0::/48",
    "2606:4700:d1::/48",
    "2606:4700:3030::/48",
    "2606:4700:3033::/48",
    "2a06:98c1:3100::/48",
    "2a06:98c1:3102::/48",
    "2a06:98c1:3120::/48",
    "2803:f800::/48",
    "2400:cb00::/48",
    "2405:8100::/48",
]

TEST_HOST = "speed.cloudflare.com"


def gen_candidates(segments, per_seg, seed=None):
    rnd = random.Random(seed)
    out = []
    for seg in segments:
        try:
            net = ipaddress.ip_network(seg, strict=False)
        except ValueError:
            continue
        base = int(net.network_address)
        size = net.num_addresses
        if size <= per_seg:
            for i in range(1, size):
                out.append(str(ipaddress.ip_address(base + i)))
        else:
            seen = set()
            while len(seen) < per_seg:
                seen.add(base + rnd.randrange(1, size))
            out.extend(str(ipaddress.ip_address(x)) for x in sorted(seen))
    return out


def tcp_latency(ip, port=443, timeout=3.0):
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.settimeout(timeout)
    t0 = time.perf_counter()
    try:
        s.connect((ip, port))
        return (time.perf_counter() - t0) * 1000.0
    except Exception:
        return None
    finally:
        try:
            s.close()
        except Exception:
            pass


def https_download(ip, nbytes=500_000, timeout=12.0):
    """对单个 IP 做 HTTPS 下载测速，返回 字节/秒 或 None"""
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, 443))
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ss = ctx.wrap_socket(s, server_hostname=TEST_HOST)
        req = (
            f"GET /__down?bytes={nbytes} HTTP/1.1\r\n"
            f"Host: {TEST_HOST}\r\n"
            "User-Agent: cf-picker/1.0\r\n"
            "Accept: */*\r\nConnection: close\r\n\r\n"
        ).encode()
        t0 = time.perf_counter()
        ss.sendall(req)
        total = 0
        while True:
            chunk = ss.recv(65536)
            if not chunk:
                break
            total += len(chunk)
        dt = time.perf_counter() - t0
        return (total / dt) if dt > 0 else 0.0
    except Exception:
        return None
    finally:
        try:
            s.close()
        except Exception:
            pass


def fmt_speed(bps):
    if bps >= 1_000_000:
        return f"{bps/1_000_000:.2f} MB/s"
    if bps >= 1000:
        return f"{bps/1000:.1f} KB/s"
    return f"{bps:.0f} B/s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--per-seg", type=int, default=3, help="每个段采样候选数")
    ap.add_argument("-t", "--timeout", type=float, default=3.0, help="TCP 超时(秒)")
    ap.add_argument("-c", "--concurrency", type=int, default=32, help="并发数")
    ap.add_argument("-f", "--file", help="候选文件（每行一个 IPv6 或 CIDR）")
    ap.add_argument("-d", "--download", action="store_true", help="对 Top5 做下载测速")
    ap.add_argument("-b", "--bytes", type=int, default=500_000, help="下载测速字节数")
    ap.add_argument("--top", type=int, default=10, help="最终展示条数")
    args = ap.parse_args()

    segs = CF_SEGMENTS
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            segs = [ln.strip() for ln in fh if ln.strip()]

    cands = gen_candidates(segs, args.per_seg, seed=20260911)
    print(f"候选节点 {len(cands)} 个，开始延迟扫描（超时 {args.timeout}s，并发 {args.concurrency}）...\n")

    results = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(tcp_latency, ip, 443, args.timeout): ip for ip in cands}
        done = 0
        for f in as_completed(futs):
            ip = futs[f]
            ms = f.result()
            done += 1
            if ms is not None:
                results.append((ms, ip))
            if done % 20 == 0 or done == len(cands):
                print(f"  进度 {done}/{len(cands)}  可用 {len(results)}", end="\r")
    print()

    if not results:
        print("没有可用节点。请先确认当前网络有 IPv6（浏览器打开 test-ipv6.com）。")
        return

    results.sort(key=lambda x: x[0])
    print(f"\n可用节点 {len(results)}/{len(cands)}\n")

    speed_map = {}
    if args.download:
        print("对 Top5 做下载测速...\n")
        for ms, ip in results[:5]:
            bps = https_download(ip, args.bytes, timeout=12.0)
            if bps:
                speed_map[ip] = bps

    print(f"{'#':>3}  {'延迟':>9}  {'节点地址':<44}  下载速度")
    print("-" * 78)
    for i, (ms, ip) in enumerate(results[: args.top], 1):
        sp = fmt_speed(speed_map[ip]) if ip in speed_map else "-"
        print(f"{i:>3}  {ms:>7.1f}ms  {ip:<44}  {sp}")

    best = results[0][1]
    print("\n>>> 推荐填进客户端 address 字段的最优节点：")
    print(f"    {best}")


if __name__ == "__main__":
    main()
