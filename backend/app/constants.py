from typing import Optional

CATEGORY_OPTIONS = [
    "主动权益",
    "指增",
    "被动指数",
    "固收+",
    "固收",
    "QDII",
    "其他",
]

CATEGORY_SET = set(CATEGORY_OPTIONS)

NON_RATED_CATEGORIES = {"被动指数", "其他"}
EQUITY_CATEGORIES = {"主动权益", "指增", "QDII"}
BOND_CATEGORIES = {"固收+", "固收"}

# Map common Tushare fund_type / user-friendly names to the PRD category set.
CATEGORY_ALIASES = {
    "股票型": "主动权益",
    "混合型": "主动权益",
    "偏股混合型": "主动权益",
    "偏债混合型": "固收+",
    "灵活配置型": "主动权益",
    "债券型": "固收",
    "纯债型": "固收",
    "短债型": "固收",
    "货币型": "其他",
    "货币市场型": "其他",
    "指数型": "被动指数",
    "股票指数": "被动指数",
    "指数增强": "指增",
    "指数增强型": "指增",
    "qdii": "QDII",
    "QDII基金": "QDII",
    "商品型": "其他",
    "FOF": "其他",
    "FOF基金": "其他",
    "REITs": "其他",
    "短期理财": "其他",
}


def normalize_category(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = value.strip()
    if key in CATEGORY_SET:
        return key
    return CATEGORY_ALIASES.get(key)
