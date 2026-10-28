#!/usr/bin/env python3
"""Small static check of the portable W-12 pack; never connects to a DB."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

PACK = Path(__file__).resolve().parent
ROOT = PACK.parents[1]
MANIFEST = PACK / "manifest.sha256"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_key(path: Path) -> str:
    return str(path.relative_to(PACK)) if path.is_relative_to(PACK) else "../../" + str(path.relative_to(ROOT))


def slug(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "").lower()
    return "".join(
        "-" if ch == " " else ch
        for ch in text
        if ch in " -_" or unicodedata.category(ch)[0] in "LN"
    )


def markdown_ids(text: str) -> set[str]:
    counts: dict[str, int] = {}
    result: set[str] = set()
    in_fence = False
    for line in text.splitlines():
        if re.match(r"\s*(```|~~~)", line):
            in_fence = not in_fence
        if in_fence:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            value = slug(match[1])
            n = counts.get(value, 0)
            result.add(value if n == 0 else f"{value}-{n}")
            counts[value] = n + 1
    return result


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.assets: list[str] = []
        self.errors: list[str] = []
        self.stack: list[str] = []
        self.lang = ""
        self.h1 = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "html":
            self.lang = data.get("lang", "") or ""
        if tag == "h1":
            self.h1 += 1
        value = data.get("id")
        if value:
            if value in self.ids:
                self.errors.append(f"duplicate id: {value}")
            self.ids.add(value)
        if tag == "a" and data.get("href") is not None:
            self.links.append(data["href"] or "")
        for name in ("src", "poster"):
            if data.get(name):
                self.assets.append(data[name] or "")
        if tag == "link" and data.get("href"):
            self.assets.append(data["href"] or "")
        if tag == "base":
            self.errors.append("base URL breaks portability")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unbalanced closing tag: {tag}")
        else:
            self.stack.pop()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true", help="write W-12 hashes after successful static checks")
    args = parser.parse_args()
    errors: list[str] = []
    files = sorted(p for p in PACK.rglob("*") if p.is_file() and p != MANIFEST)
    entrypoint = ROOT / "README.md"
    if entrypoint.exists():
        files.append(entrypoint)
    else:
        errors.append("root README.md absent")
    for name in ("checkpoint-now.md", "checkpoint-now.html", "index.html"):
        if not (PACK / name).exists():
            errors.append(f"entrypoint absent: {name}")
    pages: dict[Path, Page] = {}
    id_cache: dict[Path, set[str]] = {}
    local_links = 0
    external_links = 0

    for path in files:
        if path.is_symlink():
            errors.append(f"symlink is not portable: {path.name}")
        if path.suffix in {".md", ".html", ".json", ".py", ".sql"}:
            source = path.read_text(encoding="utf-8")
            if not source.endswith("\n") or any(line != line.rstrip() for line in source.splitlines()):
                errors.append(f"{path.name}: missing final newline or trailing whitespace")
        if path.suffix == ".html":
            page = Page()
            page.feed(path.read_text(encoding="utf-8"))
            page.close()
            if page.lang != "ru" or page.h1 != 1 or page.stack:
                page.errors.append("expected lang=ru, one h1 and balanced HTML")
            # A portable document must not need a remote font/script/image/server.
            if page.assets:
                page.errors.append(f"non-inline assets: {page.assets}")
            if re.search(r"(?:@import|url\s*\()", path.read_text(encoding="utf-8")):
                page.errors.append("CSS dependency found")
            errors.extend(f"{path.name}: {error}" for error in page.errors)
            pages[path] = page
            id_cache[path] = page.ids

    for path in files:
        if path.suffix not in {".md", ".html"}:
            continue
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".html":
            links = pages[path].links
        else:
            links = re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", content)
        for link in links:
            parsed = urlsplit(link)
            if parsed.scheme in {"http", "https", "mailto"}:
                external_links += 1
                continue
            if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
                errors.append(f"{path.name}: nonportable link {link}")
                continue
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            local_links += 1
            planned_manifest = args.write_manifest and target == MANIFEST
            if not target.is_relative_to(ROOT) or (not target.exists() and not planned_manifest):
                errors.append(f"{path.name}: missing/outside repo {link}")
                continue
            if parsed.fragment:
                if target not in id_cache:
                    if target.suffix == ".md":
                        id_cache[target] = markdown_ids(target.read_text(encoding="utf-8"))
                    elif target.suffix == ".html":
                        page = Page()
                        page.feed(target.read_text(encoding="utf-8"))
                        id_cache[target] = page.ids
                    else:
                        errors.append(f"{path.name}: cannot check fragment in {link}")
                        continue
                if unquote(parsed.fragment) not in id_cache[target]:
                    errors.append(f"{path.name}: missing anchor {link}")

    memo = PACK / "decisions-note.md"
    words = len(re.findall(r"\S+", memo.read_text(encoding="utf-8")))
    if words > 220:
        errors.append(f"memo exceeds conservative 220-token-word layout budget: {words}")

    # Check syntax without writing pycache or importing DB/third-party packages.
    for path in files:
        if path.suffix == ".py":
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except SyntaxError as error:
                errors.append(f"{path.name}: {error}")
        elif path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError) as error:
                errors.append(f"{path.name}: {error}")

    if not args.write_manifest:
        if not MANIFEST.exists():
            errors.append("manifest.sha256 absent; first run --write-manifest")
        else:
            expected: dict[str, str] = {}
            for line in MANIFEST.read_text(encoding="utf-8").splitlines():
                match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
                if not match:
                    errors.append("malformed manifest line")
                    continue
                key = match[2]
                if key in expected:
                    errors.append(f"duplicate manifest entry: {key}")
                expected[key] = match[1]
            actual = {manifest_key(p): digest(p) for p in files}
            if actual != expected:
                changed = sorted(set(actual) | set(expected))
                errors.extend(f"manifest mismatch: {name}" for name in changed if actual.get(name) != expected.get(name))

    if errors:
        print(json.dumps({"status": "FAIL", "method": "static_only", "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    if args.write_manifest:
        MANIFEST.write_text("".join(f"{digest(path)}  {manifest_key(path)}\n" for path in files), encoding="utf-8")
    print(json.dumps({
        "status": "PASS", "method": "static_only", "files_hashed": len(files),
        "local_links_checked": local_links, "external_links_not_fetched": external_links,
        "html_pages": len(pages), "memo_whitespace_words_including_title": words,
        "manifest": "written" if args.write_manifest else "verified",
        "postgresql_executed": False,
        "limits": "Half-page is a layout target; no PDF pagination, SQL execution or human rehearsal was tested."
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
