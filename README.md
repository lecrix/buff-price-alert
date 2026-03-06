# 🔔 Buff 饰品价格监控

自动监控 [buff.163.com](https://buff.163.com) 上指定 CS2 饰品的在售价格，发现低价时通过微信推送通知。

## ✨ 功能

- 🎯 灵活配置多款监控饰品，支持自定义磨损值区间
- 📊 智能比价：最低价与第二低价对比，差价超过阈值才通知
- 📱 微信实时推送（通过 Server酱）
- ⏰ 可配置监控时段（默认 9:00-24:00）
- 🔄 多饰品轮转查询，控制请求频率
- 📝 运行日志自动保存

---

## 🚀 快速开始

### 1. 安装 Python 依赖

```bash
cd buff-price-alert
pip install -r requirements.txt
```

### 2. 获取 Buff Cookie

> Cookie 是你在 buff 网站上的登录凭证，脚本通过它来访问在售列表。

**步骤：**

1. 用 Chrome 浏览器打开 [buff.163.com](https://buff.163.com) 并**登录**
2. 按 **F12** 打开开发者工具
3. 点击顶部的 **「Network」（网络）** 标签页
4. 在 buff 页面上随便点击一个饰品（触发一个网络请求）
5. 在 Network 列表中找到任意一个对 `buff.163.com` 的请求，点击它
6. 在右侧的 **「Headers」（标头）** 面板中，找到 **「Request Headers」**
7. 找到 `Cookie:` 这一行，它的值是一个很长的字符串
8. **右键 → 复制值**，粘贴到 `config.yaml` 中的 `buff_cookie` 字段

> ⚠️ **注意**：Cookie 会在几天到几周后过期，届时需要重新获取。建议使用小号。

### 3. 注册 Server酱并获取 SendKey

1. 打开 [sct.ftqq.com](https://sct.ftqq.com)
2. 用微信扫码登录
3. 登录后，在页面上可以看到你的 **SendKey**，复制它
4. 粘贴到 `config.yaml` 中的 `serverchan_key` 字段
5. 关注「方糖」服务号（Server酱会提示你），这样才能收到推送

> 💡 免费版每天可推送 5 条消息，对于低价提醒通常够用。

### 4. 配置监控饰品

```bash
# 复制配置模板
copy config.example.yaml config.yaml
```

编辑 `config.yaml`，填入你的 Cookie、SendKey，以及要监控的饰品。

**如何找到商品的 goods_id？**

打开 buff 上某款饰品的页面，URL 中的数字就是 goods_id：
```
https://buff.163.com/goods/34474
                            ↑
                       这个就是 goods_id
```

**配置示例：**
```yaml
items:
  - name: "AK-47 | 火蛇 (久经沙场)"
    goods_id: 34474
    min_paintwear: 0.15
    max_paintwear: 0.18
```

### 5. 运行脚本

```bash
python main.py
```

脚本会开始循环监控，终端显示查询日志。按 `Ctrl+C` 停止。

---

## 🧪 测试各模块

在正式运行前，你可以单独测试每个模块：

```bash
# 测试价格分析逻辑（不需要网络）
python analyzer.py

# 测试 Server酱推送（需要配置好 SendKey）
python notifier.py

# 测试 Buff API 连通性（需要配置好 Cookie）
python buff_api.py
```

---

## ⚙️ 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `buff_cookie` | - | Buff 登录 Cookie |
| `serverchan_key` | - | Server酱 SendKey |
| `schedule.start_hour` | `9` | 监控开始时间 |
| `schedule.end_hour` | `24` | 监控结束时间 |
| `request_interval` | `30` | 每款饰品间的查询间隔（秒） |
| `price_threshold_percent` | `10` | 最低价低于第二低价的百分比阈值 |
| `notify_cooldown_minutes` | `30` | 同一饰品的通知冷却时间（分钟） |

---

## ❓ 常见问题

**Q: Cookie 怎么过期了？**
> 重新在浏览器登录 buff，按上面步骤重新获取 Cookie，粘贴到 config.yaml。

**Q: 微信收不到推送？**
> 1. 确认已关注「方糖」服务号
> 2. 运行 `python notifier.py` 测试推送
> 3. 检查 SendKey 是否正确

**Q: 请求被限流了怎么办？**
> 增大 `request_interval`（如改为 60 秒），或减少监控饰品数量。

**Q: 怎么后台运行？**
> Windows 上可以用 `pythonw main.py` 运行（无窗口），或者写一个 `.bat` 脚本。
