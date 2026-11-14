"""Recompute distributed raw statistics and citation offsets from an explicitly supplied corpus."""
import argparse
import collections
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=pathlib.Path, required=True, help='Path to the original subtitle Markdown attachment.')
    args = parser.parse_args()
    try:
        raw = args.source.read_bytes()
        lines = raw.decode('utf-8-sig').splitlines()
        expected = json.loads((ROOT / 'references' / 'raw-statistics.json').read_text(encoding='utf-8'))
        evidence = json.loads((ROOT / 'references' / 'evidence.json').read_text(encoding='utf-8'))
        if hashlib.sha256(raw).hexdigest() != expected['source_sha256']:
            raise ValueError('附件SHA256与本次分析版本不同，请使用原附件或重新建立统计。')
        starts = [(i, re.match(r'## (\d+)\. (.+)', s)) for i, s in enumerate(lines)]
        starts = [(i, m) for i, m in starts if m]
        episodes = []
        for k, (start, match) in enumerate(starts):
            end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
            body_lines = []
            active = False
            for line_number in range(start, end):
                line = lines[line_number]
                if line.startswith('- 链接：'):
                    active = True
                    continue
                if active and (line == '---' or line.startswith(('# ', '## ', '<a '))):
                    break
                if active and line.strip() and not line.startswith('>'):
                    body_lines.append((line_number + 1, line))
            title = match.group(2)
            series = next((s for s in expected['series'] if s in title), '其他')
            episodes.append({'id': int(match.group(1)), 'body': '\n'.join(s for _, s in body_lines), 'lines': [n for n, _ in body_lines], 'series': series})
        assert len(episodes) == expected['episode_count']
        chars = sum(len(re.sub(r'\s', '', e['body'])) for e in episodes)
        assert chars == expected['body_chars_no_space']
        assert sum(len(re.findall(r'[\u3400-\u9fff]', e['body'])) for e in episodes) == expected['body_han_chars']
        counts = collections.Counter(e['series'] for e in episodes)
        for series, summary in expected['series'].items():
            assert counts[series] == summary['episodes']
        for phrase, summary in expected['phrases'].items():
            assert sum(e['body'].count(phrase) for e in episodes) == summary['total'], phrase
            assert sum(phrase in e['body'] for e in episodes) == summary['episodes'], phrase
        for item in evidence:
            episode = next(e for e in episodes if e['id'] == item['id'])
            assert episode['lines'] == item['source_body_lines']
            assert episode['body'][item['start']:item['end']] == item['quote'], item
        print(json.dumps({'pass': True, 'episodes': len(episodes), 'raw_nonwhitespace_chars': chars, 'phrases_checked': len(expected['phrases']), 'quotes_checked': len(evidence), 'scope': 'Raw subtitles including advertisements. No historical or audio verification.'}, ensure_ascii=False, indent=2))
    except (OSError, UnicodeError, ValueError, AssertionError, StopIteration, KeyError) as error:
        print(json.dumps({'pass': False, 'error': repr(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
