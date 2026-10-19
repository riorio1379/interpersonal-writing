#!/usr/bin/env python3
"""対人文章の機械検査。

人に送る文面のファイルを読み、敬語の誤り・丁寧すぎ・型の抜け（宛名・名乗り・署名）を数える。
直すかどうかの判断はしない。疑わしい箇所を決まった基準で拾うだけ。

使い方:
    python3 check.py 文面.txt --level 4 --medium email [--context job] [--subject "件名"]
    python3 check.py - --level 0 --medium chat < 文面.txt
    python3 check.py 文面.txt --level 4 --medium email --json

ファイルの中に「──────」だけの行が2本あれば、その間だけを本文として検査する。
Python 3.11 以上。標準ライブラリだけで動く。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES_FILE = HERE / "rules_ja.toml"
DEFAULT_PROFILE = Path.home() / ".config" / "interpersonal-writing" / "profile.md"
SEPARATOR = re.compile(r"^\s*─{6,}\s*$")
MEDIA = ("email", "chat", "form", "marketplace")

# 1通の中で重ねると丁寧すぎに見える語（SKILL.md「4. 書く」）
POLITE_MARKERS = {
    "させていただ": "させていただく",
    "存じ": "存じます",
    "恐れ入": "恐れ入ります",
    "恐縮": "恐縮です",
    "幸いです": "幸いです",
    "申し訳": "申し訳",
    "何卒": "何卒",
    "大変": "大変",
}
# 1文の中の敬語の重なりを数える目印
STACK_MARKERS = ("いただ", "存じ", "させて", "申し上げ", "恐れ入", "恐縮", "賜", "させていただ")

# 常体の文末（段階2以上で、敬体と混ざっていないかを見る）
PLAIN_END = re.compile(r"(だ|である|だった|だろう|じゃん|だよ|だね|よね|だけど|しよう)[。！!？?]?$")
POLITE_END = re.compile(r"(です|ます|ました|でした|ません|ましょう|ください|ございます)[。！!？?]?$")

# 段階0・1（家族・友人）で改まりすぎの目印
FORMAL_IN_CASUAL = re.compile(r"(いたします|申し上げ|いただけますでしょうか|存じます|恐れ入ります|ございます)")

ADDRESS = re.compile(r"(様|御中|先生|各位|殿)\s*$")
GREETING_L4 = re.compile(r"(お世話になっております|お世話になります|ご連絡ありがとうございます|ご返信ありがとうございます)")
GREETING_L5 = re.compile(r"(初めてご連絡|はじめてご連絡|突然のご連絡|突然のメール|初めてメール|はじめまして|初めまして)")
WEEKDAYS = "月火水木金土日"
DATE_JA = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日\s*[（(]([月火水木金土日])(?:曜日?)?[）)]")
DATE_SLASH = re.compile(r"(?<![\d/])(?:(\d{4})/)?(\d{1,2})/(\d{1,2})\s*[（(]([月火水木金土日])(?:曜日?)?[）)]")
EMAIL_ADDR = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"0\d{1,4}[-‐ー−]?\d{1,4}[-‐ー−]?\d{3,4}")


@dataclass
class Finding:
    category: str  # 誤り／注意／型
    line: int  # 元のファイルでの行番号（0＝文面全体）
    text: str  # 見つかった語
    message: str
    fix: str = ""
    source: str = ""


def load_body(path: str) -> tuple[list[str], int]:
    """文面を読み、検査する行と、その先頭が元のファイルの何行目かを返す。"""
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    marks = [i for i, line in enumerate(lines) if SEPARATOR.match(line)]
    if len(marks) >= 2:
        return lines[marks[0] + 1 : marks[1]], marks[0] + 1
    return lines, 0


def load_profile(arg: str | None) -> tuple[dict | None, Path]:
    """profile.md の ```toml ブロックを読む。ファイルが無ければ None。"""
    path = Path(arg or os.environ.get("INTERPERSONAL_WRITING_PROFILE") or DEFAULT_PROFILE).expanduser()
    if not path.exists():
        return None, path
    m = re.search(r"```toml\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    return (tomllib.loads(m.group(1)) if m else {}), path


def load_rules() -> list[dict]:
    with RULES_FILE.open("rb") as f:
        return tomllib.load(f).get("rule", [])


def applies(rule: dict, level: int, medium: str) -> bool:
    if not rule.get("min_level", 0) <= level <= rule.get("max_level", 5):
        return False
    media = rule.get("media")
    return not media or medium in media


def is_quote(line: str) -> bool:
    """返信の引用行（> で始まる）は検査しない。"""
    return line.lstrip().startswith((">", "＞"))


def sentences(lines: list[str], offset: int):
    """（行番号, 文）を順に返す。文は 。！？ と改行で区切る。"""
    for i, line in enumerate(lines):
        if is_quote(line):
            continue
        for s in re.split(r"(?<=[。！？!?])", line):
            s = s.strip()
            if s:
                yield offset + i + 1, s


def check_rules(lines, offset, level, medium, rules) -> list[Finding]:
    out = []
    for rule in rules:
        if not applies(rule, level, medium):
            continue
        pattern = re.compile(rule["pattern"])
        for i, line in enumerate(lines):
            if is_quote(line):
                continue
            for m in pattern.finditer(line):
                out.append(Finding(rule["category"], offset + i + 1, m.group(0), rule["message"], rule.get("fix", ""), rule.get("source", "")))
    return out


def check_politeness(lines, offset, level) -> list[Finding]:
    out = []
    if level <= 1:
        for n, s in sentences(lines, offset):
            for m in FORMAL_IN_CASUAL.finditer(s):
                out.append(Finding("注意", n, m.group(0), "家族・友人宛にしては改まりすぎ", "くだけた言い方に", "references/levels.md"))
        return out
    body = "\n".join(line for line in lines if not is_quote(line))
    for key, label in POLITE_MARKERS.items():
        count = body.count(key)
        if count >= 2:
            where = [offset + i + 1 for i, line in enumerate(lines) if key in line and not is_quote(line)]
            out.append(Finding("注意", where[0], label, f"1通に「{label}」が{count}回（{'・'.join(map(str, where))}行目）。重ねると丁寧すぎに見える", "1回に減らす", "SKILL.md 4. 書く／ビジネスメール実態調査2026"))
    for n, s in sentences(lines, offset):
        hits = sum(s.count(k) for k in STACK_MARKERS)
        if hits >= 3:
            out.append(Finding("注意", n, s[:30], f"1文に敬語の目印が{hits}個。回りくどくなっていないか", "動詞を一つにして言い切る", "敬語の指針（適度な敬語）"))
    return out


def check_style_mix(lines, offset, level, medium) -> list[Finding]:
    if level < 2:
        return []
    plain, polite = [], 0
    for n, s in sentences(lines, offset):
        if s.startswith(("・", "-", "*", "【", "1", "2", "3", "4", "5", "6", "7", "8", "9", "①")):
            continue  # 箇条書き・見出しは常体でよい
        if POLITE_END.search(s):
            polite += 1
        elif PLAIN_END.search(s):
            plain.append((n, s))
    if polite and plain:
        return [Finding("注意", n, s[-12:], "です・ます の文面に常体の文が混ざっている", "です・ます にそろえる", "公用文作成の考え方 p.(7)") for n, s in plain]
    return []


def nonempty(lines, offset):
    return [(offset + i + 1, line.strip()) for i, line in enumerate(lines) if line.strip() and not line.strip().startswith("件名")]


def signature_block(lines, offset):
    """末尾の段落（空行で区切られた最後のかたまり）を署名とみなす。2行未満なら None。"""
    block = []
    for i in range(len(lines) - 1, -1, -1):
        text = lines[i].strip()
        if not text:
            if block:
                break
            continue
        block.append((offset + i + 1, text))
    block.reverse()
    return block if len(block) >= 2 else None


def check_email(lines, offset, level, profile, context, subject) -> list[Finding]:
    out = []
    rows = nonempty(lines, offset)
    if not rows:
        return [Finding("型", 0, "", "本文が空")]
    head = rows[:8]
    tail = signature_block(lines, offset) or rows[-8:]
    if level >= 3 and not any(ADDRESS.search(t) for _, t in rows[:4]):
        out.append(Finding("型", rows[0][0], rows[0][1][:20], "冒頭に宛名（○○様／御中／先生）が無い", "", "references/ja/email.md 宛名"))
    if level == 4 and not any(GREETING_L4.search(t) or GREETING_L5.search(t) for _, t in head):
        out.append(Finding("注意", head[0][0], "", "冒頭の挨拶（お世話になっております等）が無い", "", "references/ja/email.md 挨拶"))
    if level == 5 and not any(GREETING_L5.search(t) for _, t in head):
        out.append(Finding("注意", head[0][0], "", "初めての相手なのに、初めて連絡する旨の一言が無い", "「初めてご連絡いたします」など", "references/ja/email.md 挨拶"))
    name = (profile or {}).get("name", "").replace(" ", "").replace("　", "")
    if level >= 3 and name and not any(name in t.replace(" ", "").replace("　", "") for _, t in head):
        out.append(Finding("型", head[0][0], "", f"冒頭の8行以内で名乗っていない（{name}）", "宛名・挨拶の直後に所属と氏名", "references/ja/email.md 名乗り"))
    sigs = (profile or {}).get("signatures", {})
    sig = sigs.get(context or "default") or sigs.get("default")
    tail_text = "\n".join(t for _, t in tail)
    if sig:
        for req in sig.get("required", []):
            if req not in tail_text:
                out.append(Finding("型", tail[-1][0], req, f"署名に「{req}」が無い（profile の signatures.{context or 'default'}）", "署名を profile のとおりに", "profile"))
    elif level >= 3 and not (EMAIL_ADDR.search(tail_text) or PHONE.search(tail_text)):
        out.append(Finding("注意", tail[-1][0], "", "末尾に署名（氏名・連絡先）が見当たらない", "", "references/ja/email.md 署名"))
    if subject is not None:
        if not subject.strip():
            out.append(Finding("型", 0, "", "件名が空"))
        elif level >= 4 and name and name[:2] not in subject:
            out.append(Finding("注意", 0, subject, "件名に名前が無い。受け取る側は件名だけで誰の何の用件か知りたい", "（件名）（所属 氏名）", "references/ja/email.md 件名"))
    return out


def guess_year(month: int, day: int, today: date) -> int | None:
    """年の無い日付は、今日から見ていちばん近い年とみなす（前後6か月）。"""
    best = None
    for y in (today.year - 1, today.year, today.year + 1):
        try:
            d = date(y, month, day)
        except ValueError:
            continue
        if best is None or abs((d - today).days) < abs((best - today).days):
            best = d
    return best.year if best else None


def check_weekdays(lines, offset, today: date) -> list[Finding]:
    out = []
    for i, line in enumerate(lines):
        if is_quote(line):
            continue
        for m in list(DATE_JA.finditer(line)) + list(DATE_SLASH.finditer(line)):
            y, mo, d, wd = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
            year = int(y) if y else guess_year(mo, d, today)
            try:
                real = WEEKDAYS[date(year, mo, d).weekday()] if year else None
            except ValueError:
                out.append(Finding("誤り", offset + i + 1, m.group(0), "存在しない日付"))
                continue
            if real and real != wd:
                out.append(Finding("誤り", offset + i + 1, m.group(0), f"曜日が合っていない（{year}年{mo}月{d}日は{real}曜日）", f"（{real}）", "カレンダー"))
    return out


def check_profile_rules(lines, offset, level, medium, profile) -> list[Finding]:
    out = []
    for rule in (profile or {}).get("rules", []):
        if level not in rule.get("levels", range(6)):
            continue
        if rule.get("media") and medium not in rule["media"]:
            continue
        for word in rule.get("forbid", []):
            for i, line in enumerate(lines):
                if word in line and not is_quote(line):
                    out.append(Finding(rule.get("category", "誤り"), offset + i + 1, word, rule.get("message", "profile で使わない語"), rule.get("fix", ""), "profile"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="対人文章の機械検査")
    ap.add_argument("file", help="文面のファイル（- で標準入力）")
    ap.add_argument("--level", type=int, required=True, choices=range(6), help="段階 0〜5（references/levels.md）")
    ap.add_argument("--medium", required=True, choices=MEDIA)
    ap.add_argument("--context", help="profile の署名の種類（signatures.<名前>）")
    ap.add_argument("--subject", help="件名（メールのとき）")
    ap.add_argument("--profile", help="profile.md のパス（既定は ~/.config/interpersonal-writing/profile.md）")
    ap.add_argument("--json", action="store_true", help="結果を JSON で出す")
    ap.add_argument("--today", help="曜日の検査で年を補うときの基準日（YYYY-MM-DD。既定は今日）")
    args = ap.parse_args()

    lines, offset = load_body(args.file)
    profile, ppath = load_profile(args.profile)
    findings = check_rules(lines, offset, args.level, args.medium, load_rules())
    findings += check_politeness(lines, offset, args.level)
    findings += check_style_mix(lines, offset, args.level, args.medium)
    findings += check_weekdays(lines, offset, date.fromisoformat(args.today) if args.today else date.today())
    if args.medium == "email":
        findings += check_email(lines, offset, args.level, profile, args.context, args.subject)
    findings += check_profile_rules(lines, offset, args.level, args.medium, profile)
    findings.sort(key=lambda f: ({"誤り": 0, "型": 1, "注意": 2}.get(f.category, 3), f.line))

    counts = {c: sum(f.category == c for f in findings) for c in ("誤り", "型", "注意")}
    if args.json:
        print(json.dumps({"counts": counts, "findings": [asdict(f) for f in findings], "profile": str(ppath) if profile is not None else None}, ensure_ascii=False, indent=2))
    else:
        print(f"段階{args.level}・{args.medium}" + (f"・署名={args.context}" if args.context else "") + f"（profile: {ppath if profile is not None else 'なし'}）")
        for f in findings:
            where = f"{f.line}行目" if f.line else "全体"
            fix = f" → {f.fix}" if f.fix else ""
            src = f"（{f.source}）" if f.source else ""
            word = f"「{f.text}」" if f.text else ""
            print(f"[{f.category}] {where}{word} {f.message}{fix}{src}")
        print(f"合計：誤り{counts['誤り']}・型{counts['型']}・注意{counts['注意']}")
    return 1 if counts["誤り"] or counts["型"] else 0


if __name__ == "__main__":
    sys.exit(main())
