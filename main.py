"""
main.py — Buff 饰品价格监控 主入口

轮询查询 Buff 在售列表，发现低价饰品时通过微信推送通知。
"""

import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from buff_api import get_selling_listings
from analyzer import analyze_listings
from notifier import send_wechat, format_alert_message, is_in_cooldown, mark_notified

# ---- 日志配置 ----
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging():
    """配置日志：同时输出到终端和文件。"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"monitor_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


logger = logging.getLogger("main")


def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件。"""
    path = Path(config_path)
    if not path.exists():
        logger.error("❌ 配置文件 %s 不存在！", config_path)
        logger.info("💡 请复制 config.example.yaml 为 config.yaml，并填入你的配置")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 验证必要配置
    if not config.get("buff_cookie") or config["buff_cookie"] == "在这里粘贴你的Buff Cookie":
        logger.error("❌ 请在 config.yaml 中填入有效的 Buff Cookie")
        sys.exit(1)

    if not config.get("serverchan_key") or config["serverchan_key"] == "在这里粘贴你的SendKey":
        logger.error("❌ 请在 config.yaml 中填入有效的 Server酱 SendKey")
        sys.exit(1)

    if not config.get("items"):
        logger.error("❌ 请在 config.yaml 中配置至少一个监控饰品")
        sys.exit(1)

    return config


def is_within_schedule(start_hour: int, end_hour: int) -> bool:
    """
    检查当前时间是否在监控时段内。

    Args:
        start_hour: 开始小时（如 9）
        end_hour: 结束小时（如 24，表示午夜）
    """
    current_hour = datetime.now().hour

    if end_hour == 24:
        # 24 表示一直到午夜 0 点前（即 23:59:59）
        return current_hour >= start_hour
    elif end_hour > start_hour:
        return start_hour <= current_hour < end_hour
    else:
        # 跨午夜：如 22 点到 次日 6 点
        return current_hour >= start_hour or current_hour < end_hour


def get_item_key(item: dict) -> str:
    """生成饰品的唯一标识，用于冷却计时。"""
    return f"{item['goods_id']}-{item['min_paintwear']}-{item['max_paintwear']}"


def process_item(item: dict, config: dict) -> bool:
    """
    处理单个饰品的查询和分析。

    Returns:
        True 表示成功处理（不论是否触发通知），False 表示出错。
    """
    item_name = item["name"]
    item_key = get_item_key(item)

    logger.info("━" * 50)
    logger.info("🔍 查询: %s  磨损区间: [%.4f, %.4f]",
                item_name, item["min_paintwear"], item["max_paintwear"])

    # 1. 查询在售列表
    listings = get_selling_listings(
        goods_id=item["goods_id"],
        min_paintwear=item["min_paintwear"],
        max_paintwear=item["max_paintwear"],
        cookie=config["buff_cookie"],
    )

    if listings is None:
        logger.warning("⚠️  查询失败: %s", item_name)
        return False

    if len(listings) == 0:
        logger.info("📭 暂无在售饰品: %s", item_name)
        return True

    # 2. 价格分析
    threshold = config.get("price_threshold_percent", 10)
    result = analyze_listings(listings, threshold_percent=threshold)

    if result is None:
        logger.info("✓ 价格正常: %s", item_name)
        return True

    # 3. 发现低价 — 检查冷却
    cooldown = config.get("notify_cooldown_minutes", 30)
    if is_in_cooldown(item_key, cooldown):
        return True

    # 4. 发送通知
    title, content = format_alert_message(item_name, result)
    success = send_wechat(title, content, config["serverchan_key"])

    if success:
        mark_notified(item_key)

    return True


def wait_until_schedule(start_hour: int) -> None:
    """等待到监控时段开始。"""
    now = datetime.now()
    if now.hour < start_hour:
        # 今天还没到开始时间
        wake_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    else:
        # 今天已过监控时段，等到明天
        import datetime as dt
        tomorrow = now + dt.timedelta(days=1)
        wake_time = tomorrow.replace(hour=start_hour, minute=0, second=0, microsecond=0)

    sleep_seconds = (wake_time - now).total_seconds()
    logger.info(
        "💤 当前不在监控时段，休眠到 %s（约 %.1f 小时后）",
        wake_time.strftime("%Y-%m-%d %H:%M"),
        sleep_seconds / 3600,
    )
    time.sleep(sleep_seconds)


def main():
    """主入口。"""
    setup_logging()
    logger.info("=" * 60)
    logger.info("🚀 Buff 饰品价格监控 启动")
    logger.info("=" * 60)

    # 加载配置
    config = load_config()
    items = config["items"]
    interval = config.get("request_interval", 30)
    start_hour = config.get("schedule", {}).get("start_hour", 9)
    end_hour = config.get("schedule", {}).get("end_hour", 24)

    logger.info("📋 监控 %d 款饰品，每款间隔 %d 秒", len(items), interval)
    logger.info("⏰ 监控时段: %02d:00 - %02d:00", start_hour, end_hour % 24)
    logger.info("-" * 60)

    # 主循环
    round_count = 0
    while True:
        try:
            # 检查监控时段
            if not is_within_schedule(start_hour, end_hour):
                wait_until_schedule(start_hour)
                continue

            round_count += 1
            logger.info("\n📡 === 第 %d 轮查询 (%s) ===",
                        round_count, datetime.now().strftime("%H:%M:%S"))

            # 逐一查询每个饰品
            for i, item in enumerate(items):
                # 再次检查时段（可能在循环过程中到了结束时间）
                if not is_within_schedule(start_hour, end_hour):
                    logger.info("⏰ 已到监控结束时间，停止本轮查询")
                    break

                process_item(item, config)

                # 如果不是最后一个饰品，等待间隔（加随机抖动）
                if i < len(items) - 1:
                    jitter = interval * random.uniform(0.7, 1.3)
                    logger.info("⏳ 等待 %.1f 秒后查询下一款...", jitter)
                    time.sleep(jitter)

            # 一轮结束后，等待间隔再开始下一轮（加随机抖动）
            jitter = interval * random.uniform(0.7, 1.3)
            logger.info("✅ 第 %d 轮查询完成，等待 %.1f 秒后开始下一轮...",
                        round_count, jitter)
            time.sleep(jitter)

        except KeyboardInterrupt:
            logger.info("\n\n⛔ 用户中断，程序退出。")
            break
        except Exception as e:
            logger.error("❌ 主循环异常: %s", e, exc_info=True)
            logger.info("⏳ 等待 60 秒后重试...")
            time.sleep(60)


if __name__ == "__main__":
    main()
