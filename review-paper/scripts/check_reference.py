# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""Verify that BibTeX entries correspond to real published works.

Queries CrossRef, Semantic Scholar, and OpenAlex (in that order) and reports
entries that cannot be matched, along with local red flags (missing fields,
malformed DOIs, suspicious author names, future years).

Usage: uv run check_reference.py <path> [--json] [--limit N] [--no-network] [--timeout S]
"""

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests

USER_AGENT = 'review-paper-check/1.0 (mailto:fhs@uwaterloo.ca)'
TITLE_SIM_THRESHOLD = 0.6
AUTHOR_SIM_THRESHOLD = 0.5
GENERIC_TITLE_PATTERNS = [
    r'\btowards\b',
    r'\bcomprehensive survey\b',
    r'\bnovel approach\b',
    r'\ba study on\b',
    r'\ban overview of\b',
]
SEMANTIC_SCHOLAR_SLEEP = 0.2


@dataclass
class Entry:
    """A parsed BibTeX entry.

    Attributes:
        key: Citation key (e.g., ``devlin2019bert``).
        entry_type: Entry type (e.g., ``article``, ``inproceedings``).
        file: Source ``.bib`` path.
        line: 1-based line number of the ``@type{key,`` header.
        title: Title with LaTeX braces stripped.
        authors: List of author names in ``First Last`` order where possible.
        year: Four-digit publication year, or empty string.
        doi: DOI (without URL prefix), or empty string.
        arxiv_id: arXiv identifier, or empty string.
        venue: ``booktitle`` / ``journal`` value, or empty string.
    """

    key: str
    entry_type: str
    file: str
    line: int
    title: str = ''
    authors: list[str] = field(default_factory=list)
    year: str = ''
    doi: str = ''
    arxiv_id: str = ''
    venue: str = ''


@dataclass
class Match:
    """A candidate match returned by an external database.

    Attributes:
        source: Database name (``crossref``, ``semantic_scholar``, ``openalex``).
        title: Matched title.
        authors: Matched author list.
        year: Four-digit year, or empty string.
        doi: DOI (without URL prefix), or empty string.
        title_similarity: Jaccard similarity of title tokens in ``[0, 1]``.
        author_overlap: Fraction of entry last-names also in the match, in ``[0, 1]``.
    """

    source: str
    title: str
    authors: list[str]
    year: str
    doi: str
    title_similarity: float
    author_overlap: float


@dataclass
class Verdict:
    """Outcome of verifying a single entry.

    Attributes:
        entry: The source entry.
        status: One of ``verified``, ``suspicious``, ``not_found``, ``skipped``.
        reasons: Human-readable notes (red flags, mismatch reasons).
        matches: Candidate matches from any queried source.
    """

    entry: Entry
    status: str
    reasons: list[str] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)


def strip_braces(s: str) -> str:
    """Strip outer and inner single braces from a BibTeX field value.

    Args:
        s: Raw field value, possibly wrapped in ``{...}`` or ``"..."``.

    Returns:
        The value with surrounding quotes and stray braces removed.
    """
    s = s.strip()
    if s.startswith('{') and s.endswith('}'):
        s = s[1:-1]
    elif s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s.replace('{', '').replace('}', '').strip()


def detex(s: str) -> str:
    """Remove common LaTeX escapes from a field value for fuzzy matching.

    Args:
        s: A (partially) LaTeX-escaped string.

    Returns:
        A plainer string suitable for tokenization and similarity scoring.
    """
    s = re.sub(r'\\[\'`"^~=.](\{?)([A-Za-z])\1?\}?', r'\2', s)
    s = re.sub(r'\\[A-Za-z]+\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\[A-Za-z]+', '', s)
    s = s.replace('~', ' ').replace('--', '-')
    return re.sub(r'\s+', ' ', s).strip()


def split_authors(raw: str) -> list[str]:
    """Split a BibTeX ``author`` field on `` and ``, normalizing name order.

    Args:
        raw: The raw author field, typically ``Last, First and Other, Name``.

    Returns:
        A list of ``First Last`` strings with LaTeX escapes removed.
    """
    raw = strip_braces(raw)
    parts = re.split(r'\s+and\s+', raw)
    out = []
    for p in parts:
        p = detex(p).strip()
        if not p:
            continue
        if ',' in p:
            last, first = p.split(',', 1)
            p = f'{first.strip()} {last.strip()}'
        out.append(p)
    return out


def parse_bib(text: str, filename: str) -> tuple[list[Entry], list[str]]:
    """Parse a BibTeX file into entries.

    Args:
        text: Full file contents.
        filename: Source filename, stored on each returned entry.

    Returns:
        A tuple ``(entries, errors)`` where ``errors`` are human-readable
        messages about malformed blocks that could not be parsed.
    """
    entries: list[Entry] = []
    errors: list[str] = []

    i = 0
    n = len(text)
    while i < n:
        at = text.find('@', i)
        if at < 0:
            break
        m = re.match(r'@([A-Za-z]+)\s*\{\s*([^,\s]+)\s*,', text[at:])
        if not m:
            i = at + 1
            continue
        entry_type = m.group(1).lower()
        key = m.group(2)
        if entry_type in {'comment', 'preamble', 'string'}:
            i = at + 1
            continue
        line_no = text.count('\n', 0, at) + 1
        body_start = at + m.end()
        depth = 1
        j = body_start
        while j < n and depth > 0:
            c = text[j]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            errors.append(f'{filename}:{line_no} unterminated entry @{entry_type}{{{key}')
            break
        body = text[body_start:j]
        entry = Entry(key=key, entry_type=entry_type, file=filename, line=line_no)
        for field_match in _iter_fields(body):
            name, value = field_match
            name = name.lower()
            if name == 'title':
                entry.title = detex(strip_braces(value))
            elif name == 'author':
                entry.authors = split_authors(value)
            elif name == 'year':
                y = re.search(r'(\d{4})', strip_braces(value))
                if y:
                    entry.year = y.group(1)
            elif name == 'doi':
                entry.doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', strip_braces(value)).strip()
            elif name in {'eprint', 'arxivid', 'arxiv'}:
                entry.arxiv_id = strip_braces(value).strip()
            elif name in {'booktitle', 'journal'} and not entry.venue:
                entry.venue = detex(strip_braces(value))
        entries.append(entry)
        i = j + 1
    return entries, errors


def _iter_fields(body: str) -> list[tuple[str, str]]:
    """Yield ``(field_name, raw_value)`` pairs from a BibTeX entry body.

    Args:
        body: The text between the entry's opening ``{`` and closing ``}``,
            starting just after the citation key and its trailing comma.

    Returns:
        A list of ``(name, raw_value)`` tuples. Values keep their surrounding
        braces / quotes so callers can decide how to strip them.
    """
    out: list[tuple[str, str]] = []
    i = 0
    n = len(body)
    while i < n:
        m = re.match(r'\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*', body[i:])
        if not m:
            i += 1
            continue
        name = m.group(1)
        start = i + m.end()
        if start >= n:
            break
        c = body[start]
        if c == '{':
            depth = 1
            j = start + 1
            while j < n and depth > 0:
                if body[j] == '{':
                    depth += 1
                elif body[j] == '}':
                    depth -= 1
                j += 1
            value = body[start:j]
            i = j
        elif c == '"':
            j = start + 1
            while j < n and body[j] != '"':
                if body[j] == '\\':
                    j += 2
                else:
                    j += 1
            value = body[start:j + 1]
            i = j + 1
        else:
            m2 = re.match(r'([^,]*)', body[start:])
            value = m2.group(1).strip()
            i = start + m2.end()
        out.append((name, value))
        comma = re.match(r'\s*,\s*', body[i:])
        if comma:
            i += comma.end()
    return out


def tokens(s: str) -> set[str]:
    """Lowercase alphanumeric tokens of length 2+ from a string.

    Args:
        s: Input text.

    Returns:
        A set of tokens used for Jaccard similarity.
    """
    return {t for t in re.findall(r'[A-Za-z0-9]+', s.lower()) if len(t) >= 2}


def jaccard(a: set[str], b: set[str]) -> float:
    """Compute the Jaccard similarity between two token sets.

    Args:
        a: First token set.
        b: Second token set.

    Returns:
        ``|a ∩ b| / |a ∪ b|``, or ``0.0`` if both sets are empty.
    """
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def last_name(author: str) -> str:
    """Extract a lowercase last-name token from a person name.

    Args:
        author: A person name, possibly ``Last, First`` or ``First Last``.

    Returns:
        The lowercase last word, or the whole string if it is a single token.
    """
    a = author.strip()
    if ',' in a:
        a = a.split(',', 1)[0]
    parts = [p for p in re.split(r'\s+', a) if p]
    return parts[-1].lower() if parts else ''


def author_overlap(entry_authors: list[str], match_authors: list[str]) -> float:
    """Fraction of the entry's last names that also appear in the match.

    Args:
        entry_authors: Authors from the bib entry.
        match_authors: Authors returned by the external database.

    Returns:
        A value in ``[0, 1]``. Returns ``0.0`` if either list is empty.
    """
    e = {last_name(a) for a in entry_authors if last_name(a)}
    m = {last_name(a) for a in match_authors if last_name(a)}
    if not e or not m:
        return 0.0
    return len(e & m) / len(e)


def local_red_flags(entry: Entry, now_year: int) -> list[str]:
    """Run cheap local checks on a bib entry before any API calls.

    Args:
        entry: The bib entry.
        now_year: Current calendar year; years beyond this are flagged.

    Returns:
        A list of human-readable red-flag messages (possibly empty).
    """
    flags = []
    if not entry.title:
        flags.append('missing title')
    if not entry.authors:
        flags.append('missing authors')
    if not entry.year:
        flags.append('missing year')
    else:
        try:
            y = int(entry.year)
            if y > now_year + 1:
                flags.append(f'future year {y}')
            elif y < 1900:
                flags.append(f'implausible year {y}')
        except ValueError:
            flags.append(f'non-numeric year {entry.year!r}')
    if entry.doi and not re.match(r'^10\.\d{4,9}/\S+$', entry.doi):
        flags.append(f'malformed DOI {entry.doi!r}')
    short = [a for a in entry.authors if len(re.findall(r'[A-Za-z]+', a)) < 2]
    if short:
        flags.append(f'single-token author name(s): {short}')
    if entry.title:
        low = entry.title.lower()
        for pat in GENERIC_TITLE_PATTERNS:
            if re.search(pat, low):
                flags.append(f'generic title phrase: {pat.strip(chr(92) + "b")}')
                break
    return flags


def _http_get(url: str, timeout: float) -> dict[str, Any] | None:
    """GET a URL returning JSON, with one retry on transient failure.

    Args:
        url: Request URL.
        timeout: Per-request HTTP timeout in seconds.

    Returns:
        Parsed JSON body, or ``None`` on persistent failure.
    """
    headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
    for attempt in range(2):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                time.sleep(1.0)
                continue
            return None
        except (requests.RequestException, ValueError):
            if attempt == 0:
                time.sleep(1.0)
                continue
            return None
    return None


def _score_match(entry: Entry, title: str, authors: list[str], year: str, doi: str, source: str) -> Match:
    """Build a ``Match`` with title similarity and author overlap computed.

    Args:
        entry: The bib entry being verified.
        title: Candidate title from the external source.
        authors: Candidate authors from the external source.
        year: Candidate year from the external source.
        doi: Candidate DOI from the external source.
        source: Database name for attribution.

    Returns:
        A populated ``Match`` instance.
    """
    sim = jaccard(tokens(entry.title), tokens(title))
    ov = author_overlap(entry.authors, authors)
    return Match(source=source, title=title, authors=authors, year=year, doi=doi, title_similarity=sim, author_overlap=ov)


def _rank_score(m: Match) -> float:
    """Combined rank score favouring author agreement as a tie-breaker.

    Args:
        m: A candidate match.

    Returns:
        A scalar; higher is better.
    """
    return m.title_similarity + 0.5 * m.author_overlap


def _first_author_last(entry: Entry) -> str:
    """Return the first author's last-name token, or ``''`` if unavailable.

    Args:
        entry: The bib entry.

    Returns:
        A lowercase last-name string suitable for URL query parameters.
    """
    if not entry.authors:
        return ''
    return last_name(entry.authors[0])


def query_crossref(entry: Entry, timeout: float) -> Match | None:
    """Query CrossRef for the best candidate match for a bib entry.

    Args:
        entry: The bib entry.
        timeout: Per-request HTTP timeout in seconds.

    Returns:
        The best-scoring ``Match`` from CrossRef, or ``None`` on failure.
    """
    if entry.doi:
        data = _http_get(f'https://api.crossref.org/works/{quote_plus(entry.doi)}', timeout)
        if data and 'message' in data:
            msg = data['message']
            title = (msg.get('title') or [''])[0]
            authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in msg.get('author', [])]
            year = ''
            issued = msg.get('issued', {}).get('date-parts', [[None]])
            if issued and issued[0] and issued[0][0]:
                year = str(issued[0][0])
            return _score_match(entry, title, authors, year, entry.doi, 'crossref')
    if not entry.title:
        return None
    parts = [f'query.bibliographic={quote_plus(entry.title)}', 'rows=10']
    author_q = _first_author_last(entry)
    if author_q:
        parts.append(f'query.author={quote_plus(author_q)}')
    data = _http_get(f'https://api.crossref.org/works?{"&".join(parts)}', timeout)
    if not data:
        return None
    items = data.get('message', {}).get('items', [])
    best: Match | None = None
    for it in items:
        title = (it.get('title') or [''])[0]
        authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in it.get('author', [])]
        year = ''
        issued = it.get('issued', {}).get('date-parts', [[None]])
        if issued and issued[0] and issued[0][0]:
            year = str(issued[0][0])
        cand = _score_match(entry, title, authors, year, it.get('DOI', ''), 'crossref')
        if best is None or _rank_score(cand) > _rank_score(best):
            best = cand
    return best


def query_semantic_scholar(entry: Entry, timeout: float) -> Match | None:
    """Query Semantic Scholar for the best candidate match for a bib entry.

    Args:
        entry: The bib entry.
        timeout: Per-request HTTP timeout in seconds.

    Returns:
        The best-scoring ``Match`` from Semantic Scholar, or ``None`` on failure.
    """
    if not entry.title:
        return None
    time.sleep(SEMANTIC_SCHOLAR_SLEEP)
    author_q = _first_author_last(entry)
    query_text = f'{entry.title} {author_q}'.strip()
    q = quote_plus(query_text)
    url = f'https://api.semanticscholar.org/graph/v1/paper/search?query={q}&limit=10&fields=title,authors,year,externalIds'
    data = _http_get(url, timeout)
    if not data:
        return None
    best: Match | None = None
    for it in data.get('data', []):
        title = it.get('title') or ''
        authors = [a.get('name', '') for a in it.get('authors', [])]
        year = str(it.get('year') or '')
        doi = (it.get('externalIds') or {}).get('DOI', '') or ''
        cand = _score_match(entry, title, authors, year, doi, 'semantic_scholar')
        if best is None or _rank_score(cand) > _rank_score(best):
            best = cand
    return best


def query_openalex(entry: Entry, timeout: float) -> Match | None:
    """Query OpenAlex for the best candidate match for a bib entry.

    Args:
        entry: The bib entry.
        timeout: Per-request HTTP timeout in seconds.

    Returns:
        The best-scoring ``Match`` from OpenAlex, or ``None`` on failure.
    """
    if not entry.title:
        return None
    author_q = _first_author_last(entry)
    query_text = f'{entry.title} {author_q}'.strip()
    q = quote_plus(query_text)
    url = f'https://api.openalex.org/works?search={q}&per-page=10'
    data = _http_get(url, timeout)
    if not data:
        return None
    best: Match | None = None
    for it in data.get('results', []):
        title = it.get('title') or it.get('display_name') or ''
        authors = [(a.get('author') or {}).get('display_name', '') for a in it.get('authorships', [])]
        year = str(it.get('publication_year') or '')
        doi = (it.get('doi') or '').replace('https://doi.org/', '')
        cand = _score_match(entry, title, authors, year, doi, 'openalex')
        if best is None or _rank_score(cand) > _rank_score(best):
            best = cand
    return best


def verify_entry(entry: Entry, now_year: int, timeout: float, no_network: bool) -> Verdict:
    """Run local and (optionally) external checks on a single bib entry.

    Args:
        entry: The bib entry to verify.
        now_year: Current year for future-date checks.
        timeout: Per-request HTTP timeout in seconds.
        no_network: When True, only local red-flag checks run.

    Returns:
        The verdict with status, reasons, and any candidate matches.
    """
    flags = local_red_flags(entry, now_year)
    if no_network:
        status = 'skipped' if not flags else 'suspicious'
        return Verdict(entry=entry, status=status, reasons=flags)
    matches: list[Match] = []
    for fn in (query_crossref, query_semantic_scholar, query_openalex):
        m = fn(entry, timeout)
        if m is not None:
            matches.append(m)
            if m.title_similarity >= TITLE_SIM_THRESHOLD and m.author_overlap >= AUTHOR_SIM_THRESHOLD:
                status = 'verified'
                reasons = flags[:]
                if _year_mismatch(entry, m):
                    status = 'suspicious'
                    reasons.append(f'year mismatch: bib={entry.year} {m.source}={m.year}')
                return Verdict(entry=entry, status=status, reasons=reasons, matches=matches)
    best = max(matches, key=lambda x: x.title_similarity, default=None)
    reasons = flags[:]
    if best is None:
        return Verdict(entry=entry, status='not_found', reasons=reasons, matches=matches)
    if best.title_similarity >= TITLE_SIM_THRESHOLD and best.author_overlap < AUTHOR_SIM_THRESHOLD:
        reasons.append(f'title matches {best.source} but authors diverge ({best.author_overlap:.2f})')
        return Verdict(entry=entry, status='suspicious', reasons=reasons, matches=matches)
    if best.title_similarity < TITLE_SIM_THRESHOLD:
        reasons.append(f'best title similarity {best.title_similarity:.2f} below threshold')
        return Verdict(entry=entry, status='not_found', reasons=reasons, matches=matches)
    return Verdict(entry=entry, status='suspicious', reasons=reasons, matches=matches)


def _year_mismatch(entry: Entry, match: Match) -> bool:
    """Return True if both entry and match have years and they differ by >1.

    Args:
        entry: The bib entry.
        match: A candidate match.

    Returns:
        ``True`` when years are present on both sides and differ by more than
        one (to allow preprint-vs-publication discrepancies).
    """
    if not entry.year or not match.year:
        return False
    try:
        return abs(int(entry.year) - int(match.year)) > 1
    except ValueError:
        return False


def collect_bib_files(path: Path) -> list[Path]:
    """List ``.bib`` files under a path.

    Args:
        path: A ``.bib`` file or a directory to search recursively.

    Returns:
        A sorted list of ``.bib`` paths. Empty if nothing matches.
    """
    if path.is_file():
        return [path] if path.suffix.lower() == '.bib' else []
    return sorted(path.rglob('*.bib'))


def format_human(verdicts: list[Verdict], parse_errors: list[str]) -> str:
    """Format verdicts as a grouped human-readable report.

    Args:
        verdicts: All entry verdicts.
        parse_errors: Any parse errors collected while reading the bib files.

    Returns:
        A multi-section text report.
    """
    buckets: dict[str, list[Verdict]] = {'verified': [], 'suspicious': [], 'not_found': [], 'skipped': []}
    for v in verdicts:
        buckets.setdefault(v.status, []).append(v)
    out: list[str] = []
    if parse_errors:
        out.append('## Parse errors')
        out.extend(f'- {e}' for e in parse_errors)
        out.append('')
    for name, label in [('not_found', 'Not found'), ('suspicious', 'Suspicious'), ('skipped', 'Skipped'), ('verified', 'Verified')]:
        items = buckets.get(name, [])
        if not items:
            continue
        out.append(f'## {label} ({len(items)})')
        for v in items:
            e = v.entry
            head = f'- [{e.key}] {e.file}:{e.line} — {e.title or "(no title)"}'
            out.append(head)
            for r in v.reasons:
                out.append(f'    · {r}')
            for m in v.matches:
                out.append(f'    ~ {m.source}: sim={m.title_similarity:.2f} authors={m.author_overlap:.2f} "{m.title}" ({m.year})')
        out.append('')
    totals = {k: len(buckets.get(k, [])) for k in ('verified', 'suspicious', 'not_found', 'skipped')}
    summary = (f'Summary: {totals["verified"]} verified / {totals["suspicious"]} suspicious / '
               f'{totals["not_found"]} not found / {totals["skipped"]} skipped out of {len(verdicts)}')
    out.append(summary)
    return '\n'.join(out)


def format_json(verdicts: list[Verdict], parse_errors: list[str]) -> str:
    """Format verdicts as a JSON document.

    Args:
        verdicts: All entry verdicts.
        parse_errors: Any parse errors collected while reading the bib files.

    Returns:
        A pretty-printed JSON string.
    """
    payload = {
        'parse_errors': parse_errors,
        'verdicts': [
            {
                'key': v.entry.key,
                'file': v.entry.file,
                'line': v.entry.line,
                'status': v.status,
                'reasons': v.reasons,
                'entry': {k: getattr(v.entry, k) for k in ('title', 'authors', 'year', 'doi', 'arxiv_id', 'venue')},
                'matches': [asdict(m) for m in v.matches],
            }
            for v in verdicts
        ],
    }
    return json.dumps(payload, indent=2)


def main() -> int:
    """Parse CLI arguments, run verification, and print the report.

    Returns:
        Process exit code. ``0`` when all entries verified, ``1`` if any
        entry is ``suspicious`` or ``not_found``, ``2`` on usage errors.
    """
    ap = argparse.ArgumentParser(description='Verify that BibTeX entries correspond to real works.')
    ap.add_argument('path', help='A .bib file or a directory containing .bib files.')
    ap.add_argument('--json', action='store_true', help='emit JSON instead of the grouped text report')
    ap.add_argument('--limit', type=int, default=0, help='only check the first N entries (0 = all)')
    ap.add_argument('--no-network', action='store_true', help='skip external API calls; run only local checks')
    ap.add_argument('--timeout', type=float, default=15.0, help='per-request HTTP timeout in seconds')
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f'path does not exist: {root}', file=sys.stderr)
        return 2
    files = collect_bib_files(root)
    if not files:
        print(f'no .bib files found under {root}', file=sys.stderr)
        return 2

    all_entries: list[Entry] = []
    parse_errors: list[str] = []
    for f in files:
        text = f.read_text(encoding='utf-8', errors='replace')
        entries, errors = parse_bib(text, str(f))
        all_entries.extend(entries)
        parse_errors.extend(errors)

    if args.limit and args.limit > 0:
        all_entries = all_entries[:args.limit]

    now_year = time.gmtime().tm_year
    verdicts: list[Verdict] = []
    for entry in all_entries:
        verdicts.append(verify_entry(entry, now_year, args.timeout, args.no_network))

    if args.json:
        print(format_json(verdicts, parse_errors))
    else:
        print(format_human(verdicts, parse_errors))

    bad = sum(1 for v in verdicts if v.status in {'suspicious', 'not_found'})
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
