"""
notifier.py — Server酱微信推送模块

通过 Server酱 (sctapi.ftqq.com) 将消息推送到微信。
"""

import logging
import time
import requests

logger = logging.getLogger(__name__)

# Server酱 Turbo 版 API 地址
SERVERCHAN_API = "https://sctapi.ftqq.com/{key}.send"

# 通知冷却记录：{饰品标识: 上次通知时间戳}
_cooldown_cache: dict[str, float] = {}


def is_in_cooldown(item_key: str, cooldown_minutes: int) -> bool:
    """
    检查饰品是否在通知冷却期内。

    Args:
        item_key: 饰品标识（如 "goods_id-min_pw-max_pw"）
        cooldown_minutes: 冷却时间（分钟）

    Returns:
        True 表示冷却中，不应发送通知。
    """
    last_time = _cooldown_cache.get(item_key)
    if last_time is None:
        return False

    elapsed = (time.time() - last_time) / 60
    if elapsed < cooldown_minutes:
        logger.info(
            "饰品 %s 在冷却中（已过 %.1f 分钟 / 冷却 %d 分钟），跳过通知",
            item_key, elapsed, cooldown_minutes,
        )
        return True
    return False


def mark_notified(item_key: str):
    """记录饰品的通知时间。"""
    _cooldown_cache[item_key] = time.time()


def send_wechat(
    title: str,
    content: str,
    sendkey: str,
) -> bool:
    """
    通过 Server酱推送微信消息。

    Args:
        title: 消息标题（微信通知栏显示）
        content: 消息正文（支持 Markdown 格式）
        sendkey: Server酱 SendKey

    Returns:
        True 表示发送成功。
    """
    url = SERVERCHAN_API.format(key=sendkey)

    try:
        response = requests.post(
            url,
            data={
                "title": title,
                "desp": content,
            },
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("code") == 0:
            logger.info("✅ 微信推送成功: %s", title)
            return True
        else:
            error_msg = result.get("message", "未知错误")
            logger.error("❌ Server酱返回错误: %s", error_msg)
            return False

    except requests.exceptions.RequestException as e:
        logger.error("❌ 微信推送失败: %s", e)
        return False


def format_alert_message(
    item_name: str,
    analysis_result: dict,
) -> tuple[str, str]:
    """
    格式化低价通知的标题和正文。

    Args:
        item_name: 饰品名称
        analysis_result: analyze_listings() 的返回结果

    Returns:
        (title, content) 元组
    """
    lowest = analysis_result["lowest"]
    second_lowest = analysis_result["second_lowest"]
    diff_percent = analysis_result["diff_percent"]

    title = f"🔥 低价发现: {item_name}"

    content = f"""## 💰 低价饰品提醒

**饰品**: {item_name}

---

### 最低价（低价饰品）
| 项目 | 值 |
|------|-----|
| 💲 价格 | **¥{lowest['price']:.2f}** |
| 🎯 磨损值 | {lowest['paintwear']:.6f} |

### 第二低价（参考价）
| 项目 | 值 |
|------|-----|
| 💲 价格 | ¥{second_lowest['price']:.2f} |
| 🎯 磨损值 | {second_lowest['paintwear']:.6f} |

### 差价分析
- 📉 差价百分比: **{diff_percent}%**
- 💵 节省金额: ¥{second_lowest['price'] - lowest['price']:.2f}

---

🔗 [前往 Buff 查看]({lowest['link']})

> ⏰ 低价稍纵即逝，请尽快查看！
"""

    return title, content


# ---- 模块测试入口 ----
if __name__ == "__main__":
    import yaml

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # 从 config.yaml 读取 SendKey
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("❌ 未找到 config.yaml，请先复制 config.example.yaml 并填入配置")
        exit(1)

    sendkey = config.get("serverchan_key", "")
    if not sendkey or sendkey == "在这里粘贴你的SendKey":
        print("❌ 请先在 config.yaml 中填入有效的 Server酱 SendKey")
        exit(1)

    # 发送测试消息
    print("📤 发送测试推送...")
    success = send_wechat(
        title="🧪 Buff 监控测试",
        content="如果你在微信上看到这条消息，说明 Server酱推送配置成功！\n\n> 这是一条测试消息。",
        sendkey=sendkey,
    )

    if success:
        print("✅ 发送成功！请检查微信是否收到消息。")
    else:
        print("❌ 发送失败，请检查 SendKey 是否正确。")
