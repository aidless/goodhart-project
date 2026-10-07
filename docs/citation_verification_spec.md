# 引用核验规范 (17 条台账怎么填)

## 每条必须核到的字段

| 字段 | 怎么核 | 核到什么算过 |
|---|---|---|
| doi | 从 Zotero 条目直接取 | 非空, 且能在 doi.org 解析 |
| title | 与出版商页面逐字对比 | 完全一致 (含副标题) |
| authors | 姓 + 名首字母 | 顺序一致 (作者顺序有学术含义) |
| year | 出版商页面 | 一致 |
| venue | 期刊/会议全称 | 一致 (缩写→全称) |
| verified_via | 记录来源 | 三选一: crossref / publisher / zotero-only |
| verified_date | 核验当天 | ISO 日期 |
| notes | 存疑处 | doi 解析失败等必须写明 |

## 三条纪律

1. **verified_via 必须诚实。** 只在 Zotero 里看了一眼 ≠ 核验过。
   只在 Zotero 看 = `zotero-only`, 这条记录的置信度要标低。
2. **DOI 解析失败不等于条目错。** 老论文可能无 DOI。这时 `verified_via=publisher`,
   在 notes 写「无 DOI, 经出版商页面核验」。
3. **不确定的绝不填 "ok"。** 填 `unverified` 比填一个假 ok 有价值 ——
   假 ok 会让整张表失去意义。
