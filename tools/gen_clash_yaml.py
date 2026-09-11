# -*- coding: utf-8 -*-
"""从 subscription.txt (VLESS URI) 精确解析，生成 Clash Verge/mihomo 可导入的 YAML。
用法: python gen_clash_yaml.py
输出: clash-free.yaml
"""
import re, urllib.parse

SRC = "subscription.txt"
OUT = "clash-free.yaml"
HOST_FALLBACK = "<你的pages.dev域名>"   # 占位符，部署时替换

def parse_vless(uri):
    body = uri[len("vless://"):]
    if "#" in body:
        body, remark = body.split("#", 1)
    else:
        remark = ""
    if "?" in body:
        body, qs = body.split("?", 1)
        q = dict(urllib.parse.parse_qsl(qs))
    else:
        q, qs = {}, ""
    userinfo, hostport = body.rsplit("@", 1)
    server, port = hostport.rsplit(":", 1)
    return {
        "uuid": userinfo,
        "server": server,
        "port": int(port),
        "remark": urllib.parse.unquote(remark),
        "path": q.get("path", ""),
        "sni": q.get("sni", q.get("host", HOST_FALLBACK)),
    }

def parse_ws_path(path):
    p = urllib.parse.unquote(path)
    return p if p.startswith("/") else "/" + p

def short_label(ip):
    parts = ip.split(":")
    if len(parts) >= 4 and parts[0] == "2a06":
        return f"{parts[0]}-{parts[3]}"
    if len(parts) >= 3 and parts[0] == "2606":
        return f"{parts[0]}-{parts[2]}"
    return f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else ip[:12]

def main():
    nodes = []
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("vless://"):
                nodes.append(parse_vless(line))
    if not nodes:
        print("[!] 未解析到节点"); return

    lines = []
    lines.append("# 校园网 IPv6 免流 · Clash Verge/mihomo 订阅")
    lines.append("# 由 gen_clash_yaml.py 从 subscription.txt 自动生成，勿手改节点字段")
    lines.append("# 要求: 在「校园网 IPv6」环境使用(走 IPv6 免流量)")
    lines.append("")
    lines.append("mixed-port: 7897")
    lines.append("allow-lan: false")
    lines.append("mode: rule")
    lines.append("log-level: info")
    lines.append("ipv6: true")
    lines.append("")
    lines.append("proxies:")

    names = []
    for i, n in enumerate(nodes, 1):
        label = f"CF-{i} · {short_label(n['server'])}"
        names.append(label)
        lines.append(f"  - name: \"{label}\"")
        lines.append("    type: vless")
        lines.append(f"    server: {n['server']}")
        lines.append(f"    port: {n['port']}")
        lines.append(f"    uuid: {n['uuid']}")
        lines.append("    network: ws")
        lines.append("    tls: true")
        lines.append(f"    servername: {n['sni']}")
        lines.append("    udp: true")
        lines.append("    ws-opts:")
        lines.append(f"      path: \"{parse_ws_path(n['path'])}\"")
        lines.append("      headers:")
        lines.append(f"        Host: {n['sni']}")
        lines.append("")

    lines.append("proxy-groups:")
    lines.append("  - name: \"🚀 免流\"")
    lines.append("    type: select")
    lines.append("    proxies:")
    lines.append("      - \"♻️ 自动选择\"")
    for name in names:
        lines.append(f"      - \"{name}\"")
    lines.append("      - DIRECT")
    lines.append("")
    lines.append("  - name: \"♻️ 自动选择\"")
    lines.append("    type: url-test")
    lines.append("    url: \"http://www.gstatic.com/generate_204\"")
    lines.append("    interval: 300")
    lines.append("    proxies:")
    for name in names:
        lines.append(f"      - \"{name}\"")
    lines.append("")

    lines.append("rules:")
    ruled = [
        "google.com","googleapis.com","gstatic.com","youtube.com","googlevideo.com",
        "github.com","wikipedia.org","sciencedirect.com","springer.com","wiley.com",
        "acs.org","nature.com","ieee.org","elsevier.com",
    ]
    for d in ruled:
        lines.append(f"  - DOMAIN-SUFFIX,{d},🚀 免流")
    lines.append("  - DOMAIN-SUFFIX,cnki.net,DIRECT")
    lines.append("  - DOMAIN-SUFFIX,edu.cn,DIRECT")
    lines.append("  - GEOIP,CN,DIRECT")
    lines.append("  - MATCH,🚀 免流")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[OK] 已生成 {OUT}，共 {len(nodes)} 个节点")

    text = "\n".join(lines)
    errs = []
    if "proxies:" not in text:
        errs.append("缺少 proxies 段")
    if "proxy-groups:" not in text:
        errs.append("缺少 proxy-groups 段")
    proxy_names = set(re.findall(r'^  - name: "([^"]+)"$', text, re.M))
    group_refs = set()
    for m in re.findall(r'^      - "([^"]+)"$', text, re.M):
        if m not in ("DIRECT", "♻️ 自动选择"):
            group_refs.add(m)
    if not proxy_names:
        errs.append("proxies 段未解析到任何节点")
    orphans = group_refs - proxy_names
    if orphans:
        errs.append(f"group 引用了未定义的节点: {sorted(orphans)}")
    missing = {n for n in names if n not in proxy_names}
    if missing:
        errs.append(f"部分节点未写入 proxies: {sorted(missing)}")
    if errs:
        print("  ✘ 校验失败:")
        for e in errs:
            print("     -", e)
    else:
        print("  ✔ 结构校验通过 (节点齐全, group 引用无悬空)")

if __name__ == "__main__":
    main()