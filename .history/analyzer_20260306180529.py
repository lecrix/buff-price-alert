"""
analyzer.py — 价格分析模块

对比在售列表中最低价与第二低价的差距，
判断是否存在"捡漏"机会。
"""

import logging

logger = logging.getLogger(__name__)


def analyze_listings(
    listings: list[dict],
    threshold_percent: float = 10.0,
) -> dict | None:
    """
    分析在售列表，判断最低价是否明显低于第二低价。

    Args:
        listings: 在售列表，每个元素至少包含 'price' 和 'paintwear' 字段
        threshold_percent: 价格差异阈值百分比（默认 10%）

    Returns:
        如果发现低价饰品，返回详情字典：
            {
                "lowest": {...},         # 最低价饰品信息
                "second_lowest": {...},  # 第二低价饰品信息
                "diff_percent": float,   # 差价百分比
            }
        否则返回 None。
    """
    if not listings or len(listings) < 2:
        logger.info("在售数量不足 2 件，跳过分析")
        return None

    # 按价格升序排序
    sorted_listings = sorted(listings, key=lambda x: x["price"])

    lowest = sorted_listings[0]
    second_lowest = sorted_listings[1]

    # 防止除以零
    if second_lowest["price"] <= 0:
        logger.warning("第二低价为 0 或负数，跳过分析")
        return None

    # 计算差价百分比：最低价比第二低价便宜了多少
    diff_percent = (
        (second_lowest["price"] - lowest["price"])
        / second_lowest["price"]
        * 100
    )

    logger.info(
        "价格分析: 最低 ¥%.2f (磨损 %.6f) vs 第二低 ¥%.2f (磨损 %.6f) → 差价 %.1f%%",
        lowest["price"], lowest["paintwear"],
        second_lowest["price"], second_lowest["paintwear"],
        diff_percent,
    )

    if diff_percent >= threshold_percent:
        logger.info("🎯 发现低价！差价 %.1f%% ≥ 阈值 %.1f%%", diff_percent, threshold_percent)
        return {
            "lowest": lowest,
            "second_lowest": second_lowest,
            "diff_percent": round(diff_percent, 2),
        }
    else:
        logger.debug("差价 %.1f%% < 阈值 %.1f%%，不触发通知", diff_percent, threshold_percent)
        return None


# ---- 模块测试入口 ----
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # 测试用例 1：应该触发通知（差价 20%）
    print("=== 测试 1：应触发通知 ===")
    test_listings_1 = [
        {"price": 400.0, "paintwear": 0.152, "listing_id": "a1", "goods_id": "100", "link": "#"},
        {"price": 500.0, "paintwear": 0.160, "listing_id": "a2", "goods_id": "100", "link": "#"},
        {"price": 520.0, "paintwear": 0.170, "listing_id": "a3", "goods_id": "100", "link": "#"},
    ]
    result = analyze_listings(test_listings_1, threshold_percent=10)
    assert result is not None, "❌ 应该触发通知但没有触发"
    print(f"✅ 触发！差价 {result['diff_percent']}%\n")

    # 测试用例 2：不应触发通知（差价仅 2%）
    print("=== 测试 2：不应触发通知 ===")
    test_listings_2 = [
        {"price": 490.0, "paintwear": 0.152, "listing_id": "b1", "goods_id": "100", "link": "#"},
        {"price": 500.0, "paintwear": 0.160, "listing_id": "b2", "goods_id": "100", "link": "#"},
        {"price": 520.0, "paintwear": 0.170, "listing_id": "b3", "goods_id": "100", "link": "#"},
    ]
    result = analyze_listings(test_listings_2, threshold_percent=10)
    assert result is None, "❌ 不应该触发通知但触发了"
    print("✅ 未触发，符合预期\n")

    # 测试用例 3：只有 1 件在售
    print("=== 测试 3：仅 1 件在售 ===")
    test_listings_3 = [
        {"price": 400.0, "paintwear": 0.152, "listing_id": "c1", "goods_id": "100", "link": "#"},
    ]
    result = analyze_listings(test_listings_3, threshold_percent=10)
    assert result is None, "❌ 仅 1 件应跳过"
    print("✅ 跳过，符合预期\n")

    # 测试用例 4：空列表
    print("=== 测试 4：空列表 ===")
    result = analyze_listings([], threshold_percent=10)
    assert result is None, "❌ 空列表应跳过"
    print("✅ 跳过，符合预期\n")

    print("🎉 所有测试通过！")
