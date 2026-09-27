#!/usr/bin/env python3
"""新しいセッションの最初の依頼で1回だけ、題名を「プロジェクト名：中身」に付け直すよう Claude に頼む
UserPromptSubmit hook。ピン留めの付け替えも同じ指示で頼む。

題名を変えるのは Claude 自身で、hook は指示を渡すだけ。題名とピンの道具は Claude デスクトップアプリ
（Claude Code）にしか無いので、それ以外の環境では Claude が何もせずに終わる。
"""
import json
import os
import sys
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("SESSION_TITLE_STATE_DIR", "~/.claude/hooks/state/session-title")).expanduser()
PREFIX_FILE = Path(os.environ.get("SESSION_TITLE_PREFIX_FILE", "~/.claude/session-title-prefixes.txt")).expanduser()
KEEP_DAYS = 30


def read_prefixes(path: Path) -> list[str]:
    """1行に1つ。空行と # で始まる行は読まない。"""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [s.strip() for s in lines if s.strip() and not s.strip().startswith("#")]


def build_context(prefixes: list[str], pins: bool) -> str:
    parts = [
        "このセッションの題名を付け直す。依頼の中身が分かったら、set_session_title（session_id=\"self\"）で"
        "「プロジェクト名：中身」の形にする（例「家計簿アプリ：月末の集計を直す」「調べ：新しいCLIツール」）。"
        "ツールが読み込まれていなければ ToolSearch で select:mcp__ccd_session_mgmt__set_session_title を読み込む。",
    ]
    if prefixes:
        parts.append("頭の言葉は " + "／".join(prefixes) + " のどれか。当てはまらない新しいプロジェクトなら、その名前を頭に付ける。")
    else:
        parts.append("頭の言葉は、作業しているプロジェクトやリポジトリの名前。調べものは「調べ」にする。")
    parts.append("依頼が「これどう？」だけで中身が分からないうちは仮の題名にして、分かった時点でもう一度付け直す。")
    if pins:
        parts.append(
            "改題したら続けてピンを付け替える：list_sessions で pinned が true かつ題名が同じ頭の言葉（「：」より前）で"
            "始まる別のセッションを探す（ツールは select:mcp__ccd_session_mgmt__list_sessions,mcp__ccd_sidebar__set_pinned で読み込む）。"
            "あれば set_pinned(\"self\", true) のあと、その古いほうを set_pinned(false) にする。無ければピンは触らない"
            "（今付いているピンが、本人の決めた優先リスト）。自分がピン留めされているなら、題名は「プロジェクト名：次＝◯◯」の形にして、"
            "作業の区切りで次の一手が変わるたびに付け直す。"
        )
    parts.append("これらのツールが無い環境なら何もしない。改題やピンの付け替えは、した場合だけ返事の最後に一文で伝える。")
    return "".join(parts)


def prune(state_dir: Path, now: float) -> None:
    for f in state_dir.iterdir():
        try:
            if now - f.stat().st_mtime > KEEP_DAYS * 86400:
                f.unlink()
        except OSError:
            pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    sid = str(data.get("session_id") or "").strip()
    if not sid or "/" in sid or sid.startswith("."):
        return 0
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    marker = STATE_DIR / sid
    if marker.exists():
        return 0
    marker.touch()
    prune(STATE_DIR, time.time())
    pins = os.environ.get("SESSION_TITLE_PINS", "on").lower() not in ("off", "0", "false", "no")
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": build_context(read_prefixes(PREFIX_FILE), pins),
        }
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
