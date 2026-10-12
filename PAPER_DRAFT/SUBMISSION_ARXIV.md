# arXiv 提交清单 (goodhart_arxiv_v2_source.tar.gz)

状态: 包已就绪, 实际提交需要你的 arXiv 账号与授权 (本会话无法代办)。

## 包内容 (已核验, 2026-10-12)
- main.tex (无 \includegraphics / \input, 唯一外部依赖 \bibliography{refs})
- refs.bib + main.bbl (arXiv 用 bbl 编译, bib 冗余带上无害)
- 本地编译: TinyTeX xelatex ×2, 0 error / 0 overfull / 7 页
- research_audit: PASS (0 error 0 warning)
- research_numbers 对账: PASS (252 论文数字 vs 113 数据侧数字, 0 不一致)

## 提交步骤
1. arxiv.org → Start a new submission → Category: **cs.LG** (备选 cs.AI)
2. License: CC BY 4.0 (或 arXiv 默认; 若拟投 workshop/正刊, 选不可转让者)
3. 上传 tar.gz (单文件即可, arXiv 自动解包)
4. Metadata: 标题/作者按 main.tex; abstract 从 main.tex 复制
   (⚠️ LaTeX 宏如 \exploratory 在 abstract 里需手工改成文字 [exploratory])
5. Preview 页确认无缺文件、公式渲染正常
6. Submit → 等待 moderation (通常 1–2 个工作日)

## 提交后
- arXiv 号回填: HANDOVER §13.x + paper/ 头部注释 + CLAIM_LEDGER 相关条目
- workshop CFP 追踪 (AAAI-27 workshop 未官宣; OUTLINE venue 段已定策略)
