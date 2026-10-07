"""从 Zotero 导出的 CSV 更新 citation_verification.csv。

用法:
  1. Zotero 里选中相关条目 → 文件 → 导出 → CSV
  2. python3 tools/reconcile_zotero.py zotero_export.csv prereg/citation_verification.csv

只做「按 DOI 匹配 + 回填 title/authors/year/venue」, 不做判断。
verified_via / verified_date / notes 三列留空, 由人工核验后填 ——
脚本不许伪造「已核验」。
"""
import csv
import sys
from pathlib import Path

def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def pick(row, *keys):
    for k in keys:
        if row.get(k):
            return row[k].strip()
    return ""

def main(zotero_path: str, ledger_path: str) -> int:
    z_rows = load_csv(zotero_path)
    l_path = Path(ledger_path)
    l_rows = load_csv(l_path) if l_path.exists() else []

    by_doi = {}
    for r in z_rows:
        doi = pick(r, "DOI", "doi").lower()
        if doi:
            by_doi[doi] = r

    matched = filled = 0
    for row in l_rows:
        doi = pick(row, "doi").lower()
        if not doi or doi not in by_doi:
            continue
        matched += 1
        z = by_doi[doi]
        for lk, zk in (("title", "Title"), ("year", "Publication Year"),
                       ("venue", "Publication Title"), ("authors", "Author")):
            if not row.get(lk) and z.get(zk):
                row[lk] = z[zk].strip()
                filled += 1

    if l_rows:
        with open(l_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(l_rows[0].keys()))
            w.writeheader()
            w.writerows(l_rows)

    print(f"台账 {len(l_rows)} 行, 按 DOI 匹配 {matched} 行, 回填字段 {filled} 处")
    print("提醒: verified_via/verified_date/notes 未动, 需人工核验后填。")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
