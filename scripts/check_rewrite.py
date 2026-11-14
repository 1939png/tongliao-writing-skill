"""Check same-scope rewrite length and optional literal fact anchors; no semantic claims."""
import argparse
import json
import pathlib
import re
import sys


def count(text):
    return len(re.sub(r'\s', '', text))


def evaluate(source, rewrite, anchors=None):
    source_count = count(source)
    rewrite_count = count(rewrite)
    if source_count == 0:
        raise ValueError('原稿正文为空，请提供去掉标题和附注后的正文。')
    ratio = rewrite_count / source_count
    result = {
        'source_chars': source_count,
        'rewrite_chars': rewrite_count,
        'ratio': round(ratio, 6),
        'change_percent': round((ratio - 1) * 100, 3),
        'length_pass': 85 * source_count <= 100 * rewrite_count <= 115 * source_count,
        'anchors_missing_from_source': [],
        'anchors_missing_from_rewrite': [],
        'scope': '非空白Unicode字符，含标点；输入文件应仅含正文。锚点仅检查原样出现，不验证语义。',
    }
    for anchor in anchors or []:
        if anchor not in source:
            result['anchors_missing_from_source'].append(anchor)
        if anchor not in rewrite:
            result['anchors_missing_from_rewrite'].append(anchor)
    result['literal_anchor_pass'] = not result['anchors_missing_from_source'] and not result['anchors_missing_from_rewrite']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=pathlib.Path, required=True)
    parser.add_argument('--rewrite', type=pathlib.Path, required=True)
    parser.add_argument('--anchors', type=pathlib.Path, help='Optional JSON array of exact strings, e.g. ["1890年", "约20人"].')
    args = parser.parse_args()
    try:
        source = args.source.read_text(encoding='utf-8-sig')
        rewrite = args.rewrite.read_text(encoding='utf-8-sig')
        anchors = json.loads(args.anchors.read_text(encoding='utf-8-sig')) if args.anchors else []
        if not isinstance(anchors, list) or any(not isinstance(a, str) or not a for a in anchors):
            raise ValueError('锚点文件须为由非空字符串组成的JSON数组。')
        result = evaluate(source, rewrite, anchors)
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['length_pass'] and result['literal_anchor_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
