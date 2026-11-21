#!/usr/bin/env python3
"""Diagnose mechanical risks in a Chinese draft; never claim a similarity score."""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

from analyze_corpus import PATTERNS, quantiles, split_sentences, visible_len

CATCHPHRASES = re.compile(
    r"属于是|主打一个|离谱|抽象|狠人|妙人|整活|武德充沛|丧心病狂|通辽|公屏|弹幕|吹逼小故事|赢麻了|家人们谁懂"
)
CLICHES = [
    "在这个快节奏的时代", "值得我们深思", "不禁让人", "让我们一起", "总有一种", "生活的真谛",
    "闪闪发光", "熠熠生辉", "砥砺前行", "不忘初心", "不负韶华", "未来可期", "从来都不普通",
    "平凡而伟大", "平凡的人", "时代的赞歌", "时代的川流", "匠心", "人生真谛", "这就是生活",
]
NUMBER_RE = re.compile(
    r"\d|[零〇一二两三四五六七八九十百千万亿点]+(?=年|月|日|天|个|顿|份|层|升|块|元|角|分钟|小时|分|公里|里|倍|周|岁|人|件|次|度|%|％)"
)


def diagnose(text: str) -> dict:
    text = re.sub(r"\s+", "", text)
    sentences = split_sentences(text)
    lengths = [visible_len(s) for s in sentences]
    clauses = [c for c in re.split(r"[，,；;：:。！？!?、—…\s]+", text) if visible_len(c)]
    clause_lengths = [visible_len(c) for c in clauses]
    chars = visible_len(text)
    count = max(1, len(sentences))
    catches = CATCHPHRASES.findall(text)
    cliché_hits = [p for p in CLICHES if p in text]
    feature_counts = {
        name: sum(bool(pattern.search(sentence)) for sentence in sentences)
        for name, pattern in PATTERNS.items()
    }
    questions = sum(s.endswith(("？", "?")) for s in sentences)
    numbers = sum(bool(NUMBER_RE.search(s)) for s in sentences)
    closing = text[-350:]
    closing_cliches = [p for p in cliché_hits if p in closing]
    identity_hits = re.findall(r"我是(?:新人\s*)?(?:up\s*主|UP\s*主)?\s*小约翰可汗|小约翰可汗新作|感谢大家的三连", text, re.I)

    warnings = []
    notes = []
    if not sentences:
        return {"error": "No Chinese sentences detected", "warnings": ["Input is empty or lacks sentence punctuation"]}

    short_share = 100 * sum(n <= 10 for n in lengths) / count
    very_long_share = 100 * sum(n >= 71 for n in lengths) / count
    question_share = 100 * questions / count
    number_share = 100 * numbers / count
    catch_density = 1000 * len(catches) / max(1, chars)

    if short_share > 35 and len(sentences) >= 8:
        warnings.append("短句比例偏高：把同一动作链的分句适当合并，避免写成鸡汤或营销号。")
    if very_long_share > 35 or (lengths and statistics.median(lengths) > 60):
        warnings.append("超长句偏多：检查漏标点、长定语和主语切换，但不要拆散所有动作链。")
    if clause_lengths and statistics.median(clause_lengths) > 16:
        warnings.append("分句本身偏长：优先拆长定语，让每个分句只承担一个主要信息。")
    if question_share > 18 and len(sentences) >= 8:
        warnings.append("设问较密：确认每个问题都立即由新事实回答，删除拖延式反问。")
    if chars >= 800 and number_share < 5:
        notes.append("数字句较少：这不是缺陷，但可检查规模、成本和后果是否缺少可指认的细节。")
    if catch_density > 4:
        warnings.append("口癖/评价词偏密：删去不能增加信息的标签，优先补事实、动作与因果。")
    if len(re.findall(r"至少也可以说|不说是.+?吧", text)) >= 3:
        warnings.append("谦抑升级构式重复：同一招多次使用会显模板化。")
    if text.count("没想到") >= 5:
        warnings.append("“没想到”重复：用具体新事实制造反转，而不是反复宣布反转。")
    if cliché_hits:
        warnings.append("发现可能的作文腔/套话：" + "、".join(cliché_hits))
    if len(closing_cliches) >= 2:
        warnings.append("结尾抽象套话较集中：回到具体人物、物件、影响或后续事实。")
    if identity_hits:
        warnings.append("发现本人自称或固定三连：除非用户明确要求复刻早期形式，否则删除以保持原创身份。")
    if re.search(r"[“\"].{4,}[”\"]", text):
        notes.append("文中含直接引语：请另行确认逐字来源；情境化台词不能冒充人物原话。")

    return {
        "characters": chars,
        "sentences": len(sentences),
        "sentence_length": quantiles(lengths),
        "clause_median": round(statistics.median(clause_lengths), 1) if clause_lengths else 0,
        "short_sentence_share": round(short_share, 1),
        "very_long_sentence_share": round(very_long_share, 1),
        "question_sentence_share": round(question_share, 1),
        "number_sentence_share": round(number_share, 1),
        "feature_sentence_counts": feature_counts,
        "catchphrase_count": len(catches),
        "catchphrase_per_1000_chars": round(catch_density, 2),
        "cliche_hits": cliché_hits,
        "identity_hits": identity_hits,
        "warnings": warnings,
        "notes": notes,
        "reminder": "These are mechanical diagnostics, not a factual check, quality grade, or similarity score.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="UTF-8 text or Markdown draft")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a Chinese report")
    args = parser.parse_args()
    result = diagnose(args.draft.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if "error" in result:
        print("无法诊断：" + result["error"])
        return
    print("客观诊断（不是相似度评分）")
    print(f"- 字符：{result['characters']}；句子：{result['sentences']}")
    print(f"- 句长中位数：{result['sentence_length']['median']}；分句中位数：{result['clause_median']}")
    print(f"- 短句：{result['short_sentence_share']}%；超长句：{result['very_long_sentence_share']}%")
    print(f"- 疑问句：{result['question_sentence_share']}%；数字句：{result['number_sentence_share']}%")
    print(f"- 口癖/评价词：{result['catchphrase_count']} 次，每千字 {result['catchphrase_per_1000_chars']} 次")
    if result["warnings"]:
        print("\n需要人工复核：")
        for item in result["warnings"]:
            print("- " + item)
    else:
        print("\n未发现明显的机械性风险；仍须人工检查事实、因果、笑点与结尾。")
    if result["notes"]:
        print("\n补充检查：")
        for item in result["notes"]:
            print("- " + item)


if __name__ == "__main__":
    main()
