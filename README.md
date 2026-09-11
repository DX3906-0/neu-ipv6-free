# 东北大学 · IPv6 免流方案（通用方法与智能体提示词）

> ⚠️ 本仓库只包含**通用方法**、**可复用脚本思路**与**给智能体的自动部署提示词**，**不含任何个人敏感信息**（UUID、SNI 域名、优选节点、订阅链接、本机路径均已剔除或改为 `<占位符>`）。按本方案部署后，需替换为你自己的参数。

## 目标

用**校园网 IPv6 免费流量**访问被墙外网（Google / YouTube / GitHub / 外文期刊），且不计入校园网 IPv4 计费套餐。

```
你(校园网 IPv6 2001:da8:* → 免计费)
  → Cloudflare 优选 IPv6 边缘节点
  → Cloudflare Pages 上部署的 edgetunnel Worker(VLESS + WS + TLS, SNI=你的pages.dev)
  → Worker 代为访问 IPv4 外网
```

**计费关键**：校园网通常只统计 **IPv4 下行**。只要「本机 → Cloudflare 节点」这一段走 **IPv6**，数据就免费；虽然是 Worker 帮你抓 IPv4 外网，但那段不占用你本机 IPv4。这就是"真免流"。

## 目录

| 文件 | 说明 |
|------|------|
| `docs/部署提示词.md` | 给下一个智能体(代理)的完整自动部署提示词，含步骤/验收/坑 |
| `tools/cf_ipv6_selector.py` | 校园网 IPv6 下优选最快 CF 节点（纯 Python,零依赖） |
| `tools/gen_vless.py` | 从优选 IPv6 生成 VLESS 节点与订阅（占位符版） |
| `tools/gen_clash_yaml.py` | 从订阅自动生成 Clash/mihomo 的 YAML（占位符版，附自校验） |

## 快速路径（三步）

1. **优选节点**：连校园网后 `python tools/cf_ipv6_selector.py -d`，记下最优 IPv6。
2. **生成订阅**：`python tools/gen_vless.py --ip <你的优选IPv6>`（会同时产出 base64）。
3. **生成 Clash YAML**：`python tools/gen_clash_yaml.py` → 用 Clash Verge Rev / mihomo 导入。

> 详细部署（Cloudflare Pages 建 Worker、客户端导入、手机端 clashbox 坑、验收）见 `docs/部署提示词.md`。

## 免责声明

- 免流行为可能违反校园网管理规定，**技术自用**，勿大量传播或牟利。
- 免费方案速度需由优选节点决定，CF 优选 IP 可能老化，建议每隔一两个月**重新优选一次**。
- 仅限**校园网 IPv6** 环境有效；换到手机热点(纯 IPv4)会失效并计费。