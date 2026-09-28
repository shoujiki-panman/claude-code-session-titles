"""python3 tests/test_session_title.py で実行する。追加のパッケージは要らない。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "session-title.py"


MT_ENV = {"MULMOTERMINAL_HOST": "127.0.0.1", "MULMOTERMINAL_PORT": "34567", "MULMOTERMINAL_SESSION_ID": "abc"}


def run(stdin: str, env: dict) -> str:
    # MulmoTerminal のセルの中でテストを走らせても、外側の環境変数で分岐が変わらないようにする。
    base = {k: v for k, v in os.environ.items() if not k.startswith("MULMOTERMINAL_")}
    r = subprocess.run([sys.executable, str(HOOK)], input=stdin, capture_output=True, text=True, env={**base, **env})
    assert r.returncode == 0, r.stderr
    return r.stdout


class SessionTitleHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.env = {
            "SESSION_TITLE_STATE_DIR": str(base / "state"),
            "SESSION_TITLE_PREFIX_FILE": str(base / "prefixes.txt"),
        }
        self.prefix_file = base / "prefixes.txt"

    def tearDown(self):
        self.tmp.cleanup()

    def context(self, out: str) -> str:
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]

    def test_first_prompt_gets_instruction(self):
        out = run('{"session_id":"abc"}', self.env)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("set_session_title", self.context(out))

    def test_only_once_per_session(self):
        run('{"session_id":"abc"}', self.env)
        self.assertEqual(run('{"session_id":"abc"}', self.env), "")
        self.assertNotEqual(run('{"session_id":"other"}', self.env), "")

    def test_prefix_file_is_used(self):
        self.prefix_file.write_text("# コメント\n家計簿\n\n調べ\n", encoding="utf-8")
        ctx = self.context(run('{"session_id":"abc"}', self.env))
        self.assertIn("家計簿／調べ", ctx)
        self.assertNotIn("コメント", ctx)

    def test_without_prefix_file(self):
        ctx = self.context(run('{"session_id":"abc"}', self.env))
        self.assertIn("プロジェクトやリポジトリの名前", ctx)

    def test_pins_can_be_turned_off(self):
        ctx = self.context(run('{"session_id":"abc"}', {**self.env, "SESSION_TITLE_PINS": "off"}))
        self.assertNotIn("set_pinned", ctx)
        ctx = self.context(run('{"session_id":"def"}', self.env))
        self.assertIn("set_pinned", ctx)

    def test_mulmoterminal_writes_memo_instead(self):
        ctx = self.context(run('{"session_id":"abc"}', {**self.env, **MT_ENV}))
        self.assertIn("/api/session/$MULMOTERMINAL_SESSION_ID/memo", ctx)
        self.assertNotIn("set_session_title", ctx)
        self.assertNotIn("set_pinned", ctx)

    def test_partial_mulmoterminal_env_is_ignored(self):
        ctx = self.context(run('{"session_id":"abc"}', {**self.env, "MULMOTERMINAL_PORT": "34567"}))
        self.assertIn("set_session_title", ctx)
        self.assertNotIn("/memo", ctx)

    def test_bad_input_is_silent(self):
        for stdin in ["", "{}", "not json", '{"session_id":"../x"}', '{"session_id":".hidden"}']:
            self.assertEqual(run(stdin, self.env), "", stdin)


if __name__ == "__main__":
    unittest.main()
