"""从 Zotero 导出的 CSV 更新 citation_verification.csv。

用法:
  1. Zotero 里选中相关条目 → 文件 → 导出 → CSV
  2. python3 tools/reconcile_zotero.py zotero_export.csv prereg/citation_verification.csv
     （加 --dry-run 只报告、不写盘）

只做「按 DOI 匹配 + 回填 title/authors/year/venue/zotero_key」, 不做判断。
verified / verified_via / verified_date / notes 四列永不触碰 —— 脚本不许伪造
「已核验」。

2026-10-12 修哑炮缺陷: 台账占位符是字面 `[待填]`（真值），旧代码
`if not row.get(lk)` 对占位符恒为 False → 匹配成功也回填 0 处。现以
`_is_blank` 统一判空（空串/纯空白/`[待填]` 占位符都算"待回填"），并补
zotero_key ← Zotero 导出的 Key 列回填。
"""
import csv
import sys
from pathlib import Path

PLACEHOLDER = "[待填]"

# 台账列 ← Zotero CSV 列。zotero_key 的来源是 Zotero 导出 CSV 的 Key 列
# （条目在本机 Zotero 库的内部键），verified 等人工列一律不在此表。
FIELD_MAP = (
    ("title", "Title"),
    ("year", "Publication Year"),
    ("venue", "Publication Title"),
    ("authors", "Author"),
    ("zotero_key", "Key"),
)

TOUCHABLE = {lk for lk, _ in FIELD_MAP}


def _is_blank(v):
    """台账单元视为"待回填": 空、纯空白、或字面占位符 [待填]。"""
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s == PLACEHOLDER


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pick(row, *keys):
    for k in keys:
        if row.get(k):
            return row[k].strip()
    return ""


def main(zotero_path: str, ledger_path: str, dry_run: bool = False) -> int:
    z_rows = load_csv(zotero_path)
    l_path = Path(ledger_path)
    if not l_path.exists():
        print(f"台账不存在: {l_path}")
        return 1
    l_rows = load_csv(l_path)

    by_doi = {}
    for r in z_rows:
        doi = pick(r, "DOI", "doi").lower()
        if doi:
            by_doi[doi] = r

    matched = filled = 0
    key_filled = 0
    for row in l_rows:
        doi = pick(row, "doi").lower()
        if not doi or doi not in by_doi:
            continue
        matched += 1
        z = by_doi[doi]
        for lk, zk in FIELD_MAP:
            if _is_blank(row.get(lk)) and str(z.get(zk) or "").strip():
                row[lk] = str(z[zk]).strip()
                filled += 1
                if lk == "zotero_key":
                    key_filled += 1

    # 人工核验列（verified/verified_via/verified_date/notes）唯一的写路径就是
    # FIELD_MAP 的左列集合——脚本里没有第二条写入语句，守卫靠结构而非断言。

    if dry_run:
        print(f"[dry-run] 台账 {len(l_rows)} 行, 按 DOI 匹配 {matched} 行, "
              f"回填 {filled} 处 (其中 zotero_key {key_filled} 处) —— 未写盘")
        return 0

    if l_rows:
        with open(l_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(l_rows[0].keys()))
            w.writeheader()
            w.writerows(l_rows)

    print(f"台账 {len(l_rows)} 行, 按 DOI 匹配 {matched} 行, 回填字段 {filled} 处"
          f" (其中 zotero_key {key_filled} 处)")
    print("提醒: verified/verified_via/verified_date/notes 未动, 需人工核验后填。")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], args[1], dry_run="--dry-run" in sys.argv))
