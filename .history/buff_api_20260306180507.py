"""
buff_api.py — Buff 在售列表 API 请求封装

通过 Cookie 认证访问 buff.163.com 的非官方 API，
查询指定饰品在指定磨损值区间内的在售列表。
"""

import logging
import requests

logger = logging.getLogger(__name__)

# Buff 在售列表 API 地址
SELLING_API_URL = "https://buff.163.com/api/market/goods/selling"

# 模拟浏览器的请求头
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://buff.163.com/market/goods",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


def get_selling_listings(
    goods_id: int,
    min_paintwear: float,
    max_paintwear: float,
    cookie: str,
    page_num: int = 1,
    page_size: int = 10,
) -> list[dict] | None:
    """
    查询指定饰品在指定磨损值区间内的在售列表。

    Args:
        goods_id: Buff 商品 ID（从商品页面 URL 获取）
        min_paintwear: 磨损值下限（如 0.15）
        max_paintwear: 磨损值上限（如 0.18）
        cookie: Buff 登录后的 Cookie 字符串
        page_num: 页码，默认第 1 页
        page_size: 每页数量，默认 10 条（取前几条即可）

    Returns:
        在售列表，每个元素包含 price（价格）和 paintwear（磨损值）。
        请求失败时返回 None。
    """
    params = {
        "game": "csgo",
        "goods_id": goods_id,
        "page_num": page_num,
        "page_size": page_size,
        "sort_by": "price.asc",
        "min_paintwear": str(min_paintwear),
        "max_paintwear": str(max_paintwear),
    }

    headers = {**DEFAULT_HEADERS, "Cookie": cookie}

    try:
        response = requests.get(
            SELLING_API_URL,
            params=params,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        # 检查 Buff API 返回的状态码
        if data.get("code") != "OK":
            error_msg = data.get("error", data.get("code", "未知错误"))
            logger.error("Buff API 返回错误: %s", error_msg)
            return None

        # 解析在售列表
        items = data.get("data", {}).get("items", [])
        listings = []
        for item in items:
            try:
                price = float(item.get("price", 0))
                paintwear = float(
                    item.get("asset_info", {}).get("paintwear", "0")
                )
                listing_id = item.get("id", "")
                goods_id_str = str(goods_id)

                listings.append({
                    "price": price,
                    "paintwear": paintwear,
                    "listing_id": listing_id,
                    "goods_id": goods_id_str,
                    "link": f"https://buff.163.com/goods/{goods_id_str}",
                })
            except (ValueError, TypeError) as e:
                logger.warning("解析单条在售数据失败: %s", e)
                continue

        logger.info(
            "查询成功: goods_id=%s, 磨损区间=[%.4f, %.4f], 找到 %d 条在售",
            goods_id, min_paintwear, max_paintwear, len(listings),
        )
        return listings

    except requests.exceptions.Timeout:
        logger.error("请求超时: goods_id=%s", goods_id)
        return None
    except requests.exceptions.ConnectionError:
        logger.error("网络连接失败: goods_id=%s", goods_id)
        return None
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "未知"
        if status_code == 403:
            logger.error("Cookie 可能已过期或被限制 (403): goods_id=%s", goods_id)
        elif status_code == 429:
            logger.error("请求过于频繁，被限流 (429): goods_id=%s", goods_id)
        else:
            logger.error("HTTP 错误 (%s): goods_id=%s", status_code, goods_id)
        return None
    except Exception as e:
        logger.error("未知错误: %s", e)
        return None


# ---- 模块测试入口 ----
if __name__ == "__main__":
    import yaml

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # 从 config.yaml 读取配置进行测试
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("❌ 未找到 config.yaml，请先复制 config.example.yaml 并填入配置")
        exit(1)

    cookie = config["buff_cookie"]
    items = config["items"]

    if not items:
        print("❌ 配置文件中没有监控饰品")
        exit(1)

    # 测试第一个饰品
    test_item = items[0]
    print(f"\n🔍 测试查询: {test_item['name']}")
    print(f"   磨损区间: [{test_item['min_paintwear']}, {test_item['max_paintwear']}]")

    results = get_selling_listings(
        goods_id=test_item["goods_id"],
        min_paintwear=test_item["min_paintwear"],
        max_paintwear=test_item["max_paintwear"],
        cookie=cookie,
    )

    if results is None:
        print("❌ 查询失败，请检查 Cookie 是否有效")
    elif len(results) == 0:
        print("⚠️  该区间当前没有在售饰品")
    else:
        print(f"\n✅ 找到 {len(results)} 条在售:")
        for i, item in enumerate(results, 1):
            print(f"   {i}. ¥{item['price']:.2f}  磨损: {item['paintwear']:.6f}")
