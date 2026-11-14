# 小约翰可汗 文案创作 Skill

> 我把鸽子的绝大部分视频的字幕文件全爬了出来，不包括《世纪风暴》，也不包括还没有字幕的早期系列。交给 Qwen4、Qwen3.8 Max、HY4 DeepseekV 4.1 Flash、GPT6.1 Sol 研究语言特色，最后产出了这个文案创作 Skill。效果我自己感觉还不理想，所以以后大概率会继续更新。

`xiaoyuehan-rewriter` 是一个中文叙事改稿技能：给它人物、事件或组织的原始材料，按口播稿的讲法重写——先锁主角与时间范围，用事件钩子开场，铺人物主线，靠口语叙述和贴题的歇后语收束；不写成创业英雄颂、公司年表或模板化互动。

## 语料

- 全本 168 期，合计约 179 万非空白字符，其中汉字 158 万（统计口径见 `references/raw-statistics.json`）。
- 不含《世纪风暴》，不含还没有字幕的早期系列。
- 原文随仓库分发：`小约翰字幕文本.md`（5.3 MB）。`references/raw-statistics.json` 记录了它的 SHA256 与字数，`scripts/audit_corpus.py` 可以拿这个文件重新核一遍。

## 分析产物

全本字幕分别交给四个模型做语言特色研究，再收敛成 `references/` 里的文档：

- `style-analysis.md`、`voice-and-lexicon.md`、`writing-mechanics.md`：语料层面的句长、转折、称呼、歇后语位置和段落接力习惯。
- `longform-and-flow.md`、`person-first-calibration.md`：长稿的节奏，以及人物稿的主线怎么铺、实稿怎么校准。
- `corpus-index.md`、`evidence.md`、`evidence.json`、`raw-statistics.json`：把结论钉回原文——每期用到的正文在第几行、每条论断引的是哪一段。
- `reading-coverage.md`、`semantic-review.md`：读了多少，哪些结论还只是读出来的印象、没有被逐字核对。

## 现在是什么水平

能挡住一部分模板腔：`SKILL.md` 里已经把「换一般人……但他不……」「你品品这个要求」「先认识一下这位老哥」这类句式列为默认禁用。但长稿的节奏和信息取舍仍然不稳，效果还不到理想水平。

后续大概率会继续更新，`SKILL.md` 和 `references/` 都会动。

## 仓库结构

```
SKILL.md                    技能主文件：触发条件、加载顺序、写作规程与自检
references/                 12 份语料分析、校准与证据文档
scripts/check_rewrite.py    改写稿的约束检查
scripts/audit_corpus.py     校验语料文件与仓库统计是否一致
tests/                      回归测试与 4 组样例（货梯、表格、海岛、图书馆）
小约翰字幕文本.md            168 期字幕原文（5.3 MB）
```

## 用法

1. 把整个目录放进你的 skills 目录，目录名保持 `xiaoyuehan-rewriter`。
2. 何时触发、按什么顺序读参考文件，见 `SKILL.md` 开头的「目的和加载顺序」。
3. 写人物稿先读 `person-first-calibration.md`，写长稿先读 `longform-and-flow.md`。

## 自检

```bash
python -m unittest discover -s tests -p test_check_rewrite.py   # 7 项
python scripts/audit_corpus.py --source 小约翰字幕文本.md        # 应输出 "pass": true
```

## 许可与版权

代码与文档采用 MIT。`小约翰字幕文本.md` 是第三方视频的逐字稿，版权归原作者，此处仅用于风格研究与学习；权利人提出要求会立即移除。
