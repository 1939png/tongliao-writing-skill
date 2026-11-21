#!/usr/bin/env python3
"""Reproduce aggregate style metrics for the supplied Markdown subtitle corpus.

The script deliberately exports aggregates only, not a rewritten copy of the corpus.
AI-subtitle punctuation and transcription errors make these metrics diagnostic rather
than ground truth. Use them together with close reading, not as style quotas.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

EPISODE_RE = re.compile(r"^## (\d+)\. (.+)$", re.M)
SERIES_RE = re.compile(r"【(.+?)(\d+)】")
PUNCT_RE = re.compile(r"[\s，,；;：:。！？!?、—…·《》〈〉「」『』（）()\-`'\"“”‘’]+")

PATTERNS = {
    "contrast": re.compile(r"但是|但|然而|不过|可是|却|反而|结果|没想到|虽然|尽管|与其|不料|可惜"),
    "causal": re.compile(r"因为|所以|因此|由于|于是|导致|以至于|这样一来|之所以|为此|难怪"),
    "comparison": re.compile(r"堪比|相当于|差不多|相比|一比|一样|好像|仿佛|宛如|堪称|简直是|等于是|可以算|什么概念|如同|就好像|跟.+?比"),
    "audience": re.compile(r"大家|大伙|各位|观众|你们|你品|公屏|弹幕|咱们|我们之前|我之前|兄弟|朋友"),
    "hedge": re.compile(r"可能|大概|差不多|基本上|多少|有点|有些|颇有|相对|某种|估计|应该|或许|至少|似乎|可以说|说不上"),
    "sequence": re.compile(r"此时|随后|然后|后来|接下来|紧接着|很快|不久|多年后|几年后|从此|最终|就这样|与此同时|当年|到了|等到"),
    "evaluation": re.compile(r"离谱|荒唐|魔幻|抽象|奇葩|狠人|妙人|硬核|丧心病狂|武德充沛|情绪稳定|顶级|天才|奇迹|整活|传奇|无语|尴尬|滑稽|可笑|愚蠢|聪明|疯狂"),
    "listing": re.compile(r"首先|其次|再次|最后|其一|其二|第一|第二|第三|一是|二是|一方面|另一方面"),
    "callback": re.compile(r"之前讲过|我们之前|上一期|前面说|还记得|正如|以后讲|下期|下回|开篇|前面提到|从头说起"),
    "stance": re.compile(r"应该说|可以说|不得不说|说实话|讲真|实际上|事实上|显然|当然|毫无疑问|某种意义上|起码|至少|总的来说|从总体上|按理来说|一般来说|众所周知|要知道|在我看来"),
    "self_correction": re.compile(r"啊不对|不对，|啊不是|或者说|准确地说|准确的说|反正就是|怎么说呢|这么说吧"),
}

PHRASES = [
    "大家好", "新人up主", "小约翰可汗", "每周讲一个", "吹逼小故事", "感谢大家的三连", "下期再见",
    "众所周知", "要知道", "实际上", "事实上", "应该说", "一般来说", "按理来说", "从某种意义上",
    "总的来说", "从总体上", "简单的说", "简单来说", "相比之下", "值得一提的是", "有意思的是", "有趣的是",
    "不出意外", "毫无意外", "果然", "显然", "当然", "不过", "但是", "然而", "于是", "因此", "就这样",
    "此时", "随后", "很快", "最终", "结果", "没想到", "万万没想到", "只有一个小问题", "只有一个小瑕疵",
    "问题来了", "那么问题来了", "什么概念", "怎么说呢", "答曰", "属于是", "主打一个", "有备而来",
    "来都来了", "情绪稳定", "武德充沛", "丧心病狂", "离谱", "抽象", "魔幻", "奇葩", "整活", "狠人",
    "妙人", "通辽", "公屏", "弹幕", "兄弟们", "大伙", "大家", "咱们", "我们之前", "之前讲过", "上一期",
    "前面说", "如果说是", "如果说", "与其", "不如", "本着", "在某种意义上", "从效果上看", "事实证明",
    "从这个意义上", "名义上", "物理上", "精神上", "理论上", "技术上", "字面意义上", "一对一", "一步到位",
]


def visible_len(text: str) -> int:
    return len(PUNCT_RE.sub("", text))


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", "", text)
    parts = re.findall(r"[^。！？!?]*[。！？!?]|[^。！？!?]+$", text)
    return [p for p in parts if visible_len(p) >= 2]


def quantiles(values: list[int]) -> dict[str, float | int]:
    if not values:
        return {"p10": 0, "p25": 0, "median": 0, "p75": 0, "p90": 0, "mean": 0}
    ordered = sorted(values)
    return {
        "p10": round(statistics.quantiles(ordered, n=10)[0], 1),
        "p25": round(statistics.quantiles(ordered, n=4)[0], 1),
        "median": round(statistics.median(ordered), 1),
        "p75": round(statistics.quantiles(ordered, n=4)[2], 1),
        "p90": round(statistics.quantiles(ordered, n=10)[8], 1),
        "mean": round(statistics.mean(ordered), 1),
    }


def parse_corpus(path: Path) -> list[dict]:
    source = path.read_text(encoding="utf-8")
    matches = list(EPISODE_RE.finditer(source))
    episodes = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        block = source[match.end():end]
        # The appendix follows the final transcript separator.
        block = block.split("\n---\n", 1)[0]
        date_match = re.search(r"- 发布：(\d{4}-\d{2}-\d{2})", block)
        duration_match = re.search(r"时长：(\d+):(\d+)", block)
        subtitle_match = re.search(r"字幕：.*?（(\d+) 条）", block)
        url_match = re.search(r"- 链接：(https?://\S+)", block)
        body = re.sub(r"^- 发布：.*$|^- 链接：.*$|^<a id=.*$", "", block, flags=re.M).strip()
        title = match.group(2).strip()
        series_match = SERIES_RE.search(title)
        duration = int(duration_match.group(1)) * 60 + int(duration_match.group(2)) if duration_match else 0
        episodes.append({
            "id": int(match.group(1)),
            "title": title,
            "series": series_match.group(1) if series_match else "其他",
            "series_no": int(series_match.group(2)) if series_match else 0,
            "date": date_match.group(1) if date_match else "",
            "duration_seconds": duration,
            "subtitle_entries": int(subtitle_match.group(1)) if subtitle_match else 0,
            "url": url_match.group(1) if url_match else "",
            "text": body,
        })
    return episodes


def sentence_archetype(sentence: str) -> str:
    if sentence.endswith(("？", "?")):
        return "question_or_setup"
    hits = {name for name, pattern in PATTERNS.items() if pattern.search(sentence)}
    if re.search(r"\d", sentence) and "comparison" in hits:
        return "number_plus_comparison"
    if re.search(r"\d", sentence):
        return "number_plus_fact"
    if "contrast" in hits:
        return "contrast_or_reversal"
    if "causal" in hits:
        return "causal_explanation"
    if "comparison" in hits:
        return "comparison_or_analogy"
    if "audience" in hits:
        return "audience_or_shared_context"
    if "evaluation" in hits:
        return "evaluation_or_label"
    return "plain_narrative_or_dialogue"


def analyze(episodes: list[dict]) -> tuple[dict, list[dict]]:
    all_sentences = []
    all_clauses = []
    archetypes = Counter()
    feature_sentences = Counter()
    feature_episodes = Counter()
    phrase_counts = Counter()
    phrase_episode_coverage = Counter()
    title_question = 0
    cold_open_date = 0
    cold_open_stock = 0
    greeting_anywhere = 0
    greeting_after_300 = 0
    signoff_next = 0
    signoff_triple = 0
    rows = []

    for ep in episodes:
        text = ep["text"]
        sentences = split_sentences(text)
        lengths = [visible_len(s) for s in sentences]
        clauses = [c for c in re.split(r"[，,；;：:。！？!?、—…\s]+", text) if visible_len(c)]
        clause_lengths = [visible_len(c) for c in clauses]
        all_sentences.extend(sentences)
        all_clauses.extend(clauses)
        archetypes.update(sentence_archetype(s) for s in sentences)
        if re.search(r"？|\?|如何|谁|什么|哪|为啥|怎么|为何|多少|多大", ep["title"]):
            title_question += 1
        if re.match(r"^(?:\d{4}年|\d{2,4}[./年])", text[:30]):
            cold_open_date += 1
        if text.startswith("这是一个"):
            cold_open_stock += 1
        greeting_pos = text.find("大家好")
        if greeting_pos >= 0:
            greeting_anywhere += 1
            if greeting_pos >= 300:
                greeting_after_300 += 1
        if "下期再见" in text[-1000:] or "下回分解" in text[-1000:]:
            signoff_next += 1
        if "感谢大家的三连" in text[-1000:]:
            signoff_triple += 1

        ep_hits = set()
        for name, pattern in PATTERNS.items():
            hit_count = 0
            for sentence in sentences:
                if pattern.search(sentence):
                    feature_sentences[name] += 1
                    hit_count += 1
            if hit_count:
                ep_hits.add(name)
        feature_episodes.update(ep_hits)

        for phrase in PHRASES:
            count = text.count(phrase)
            phrase_counts[phrase] += count
            if count:
                phrase_episode_coverage[phrase] += 1

        ep_counts = Counter()
        for sentence in sentences:
            for name, pattern in PATTERNS.items():
                if pattern.search(sentence):
                    ep_counts[name] += 1
        rows.append({
            "id": ep["id"],
            "date": ep["date"],
            "series": ep["series"],
            "series_no": ep["series_no"],
            "title": ep["title"],
            "duration_seconds": ep["duration_seconds"],
            "characters": visible_len(text),
            "sentences": len(sentences),
            "median_sentence_chars": round(statistics.median(lengths), 1) if lengths else 0,
            "mean_sentence_chars": round(statistics.mean(lengths), 1) if lengths else 0,
            "question_sentences": sum(s.endswith(("？", "?")) for s in sentences),
            "number_sentences": sum(bool(re.search(r"\d", s)) for s in sentences),
            **{f"{name}_sentences": ep_counts[name] for name in PATTERNS},
            "url": ep["url"],
        })

    sentence_lengths = [visible_len(s) for s in all_sentences]
    clause_lengths = [visible_len(c) for c in all_clauses]
    total_chars = sum(row["characters"] for row in rows)
    total_sentences = len(all_sentences)
    series_summary = {}
    for series in sorted({ep["series"] for ep in episodes}):
        ids = {ep["id"] for ep in episodes if ep["series"] == series}
        series_rows = [r for r in rows if r["id"] in ids]
        series_sentences = [s for ep in episodes if ep["id"] in ids for s in split_sentences(ep["text"])]
        series_lengths = [visible_len(s) for s in series_sentences]
        series_summary[series] = {
            "episodes": len(series_rows),
            "characters": sum(r["characters"] for r in series_rows),
            "sentences": len(series_sentences),
            "sentence_length": quantiles(series_lengths),
            "mean_episode_minutes": round(statistics.mean(r["duration_seconds"] for r in series_rows) / 60, 1),
            "question_sentence_share": round(100 * sum(r["question_sentences"] for r in series_rows) / max(1, len(series_sentences)), 1),
            "number_sentence_share": round(100 * sum(r["number_sentences"] for r in series_rows) / max(1, len(series_sentences)), 1),
        }

    summary = {
        "method_note": "Rule-based diagnostics over AI subtitles; punctuation, names, embedded ads and dramatized dialogue may be noisy. Categories overlap except archetypes. Not style quotas.",
        "episodes": len(episodes),
        "date_range": [min(ep["date"] for ep in episodes), max(ep["date"] for ep in episodes)],
        "characters_excluding_punctuation": total_chars,
        "sentences": total_sentences,
        "clauses": len(all_clauses),
        "sentence_length": quantiles(sentence_lengths),
        "clause_length": quantiles(clause_lengths),
        "sentence_length_buckets": {
            "2-10": round(100 * sum(2 <= n <= 10 for n in sentence_lengths) / total_sentences, 1),
            "11-25": round(100 * sum(11 <= n <= 25 for n in sentence_lengths) / total_sentences, 1),
            "26-45": round(100 * sum(26 <= n <= 45 for n in sentence_lengths) / total_sentences, 1),
            "46-70": round(100 * sum(46 <= n <= 70 for n in sentence_lengths) / total_sentences, 1),
            "71+": round(100 * sum(n >= 71 for n in sentence_lengths) / total_sentences, 1),
        },
        "question_sentence_share": round(100 * sum(s.endswith(("？", "?")) for s in all_sentences) / total_sentences, 1),
        "number_sentence_share": round(100 * sum(bool(re.search(r"\d", s)) for s in all_sentences) / total_sentences, 1),
        "archetype_shares": {k: round(100 * v / total_sentences, 1) for k, v in archetypes.most_common()},
        "feature_sentence_shares": {k: round(100 * v / total_sentences, 1) for k, v in feature_sentences.most_common()},
        "feature_episode_coverage": {k: round(100 * v / len(episodes), 1) for k, v in feature_episodes.most_common()},
        "opening_and_signoff": {
            "question_titles": title_question,
            "date_led_openings": cold_open_date,
            "this_is_a_openings": cold_open_stock,
            "greeting_anywhere": greeting_anywhere,
            "greeting_after_300_chars": greeting_after_300,
            "next_episode_signoff": signoff_next,
            "triple_support_signoff": signoff_triple,
        },
        "phrase_counts": dict(phrase_counts.most_common()),
        "phrase_episode_coverage": dict(phrase_episode_coverage.most_common()),
        "series": series_summary,
    }
    return summary, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path, help="Path to the Markdown subtitle corpus")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    episodes = parse_corpus(args.corpus)
    if not episodes:
        raise SystemExit("No episodes found; check the expected '## 1. title【series01】' format")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary, rows = analyze(episodes)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (args.output_dir / "episode-metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
