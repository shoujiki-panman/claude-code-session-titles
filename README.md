# claude-code-session-titles

Claude デスクトップアプリ（Claude Code）のセッションの題名を、Claude 自身に「プロジェクト名：中身」の形へ付け直させる UserPromptSubmit hook です。ピン留めしたセッションの付け替えも一緒に頼みます。

アプリはセッションに自動で題名を付けますが、最初の一言がほぼそのまま題名になることがあります。「きた」「次」「続きから」「これどう？」のような題名が並ぶと、どれが何のセッションか分かりません。この hook を入れると、新しいセッションの最初の依頼で、Claude が中身を見て題名を付け直します。

```
（例）
きた          →  ブログ：記事の下書きを直す
続きから      →  家計簿アプリ：月末の集計を直す
これどう？    →  調べ：新しいCLIツール
```

## 使える環境

**Claude デスクトップアプリの Code タブと、MulmoTerminal のセルです。**

- **デスクトップアプリ**：題名を変える道具とピン留めの道具を使います。
- **MulmoTerminal**：題名の道具が無いので、代わりにセッションのメモを MulmoTerminal の API（`POST /api/session/<id>/memo`）で書かせます。メモは題名として最優先で表示されます。ピンに当たるものは無いので、ピンの付け替えはしません。hook は `MULMOTERMINAL_HOST` / `MULMOTERMINAL_PORT` / `MULMOTERMINAL_SESSION_ID` の3つが揃っているかで MulmoTerminal のセルかどうかを見分けます。

それ以外（CLI やほかのアプリで開いた Claude Code）でも hook 自体は動きますが、道具が無いので Claude は何もせずに終わります。

## 動き

1. 新しいセッションで最初の依頼を送ると、hook が「題名を付け直して」という指示を Claude に渡します（`additionalContext`）
2. Claude は依頼の中身が分かった時点で、題名を「プロジェクト名：中身」に変えます
3. 同じ頭の言葉で始まる別のセッションがピン留めされていれば、ピンを新しいセッションへ移します
4. ピン留めされたセッションの題名は「プロジェクト名：次＝◯◯」の形にし、次の一手が変わるたびに付け直します

hook が指示を渡すのは、1つのセッションにつき最初の1回だけです。セッション ID の印を `~/.claude/hooks/state/session-title/` に置いて判断します（30日たった印は消します）。

題名を変えるのは Claude で、hook が渡すのは指示だけです。指示どおりに動くかは、そのときの Claude しだいです。

### ピン＝優先リスト

優先リストは別のファイルに持ちません。サイドバーで今付いているピンが、そのまま優先リストです。ピンを付け外しすれば、次のセッションからそれが反映されます。ピン留めしていないプロジェクトでは、ピンには触りません。

## 入れ方

Claude デスクトップアプリの Code タブで、このリポジトリの URL を渡して頼むだけです。

> https://github.com/shoujiki-panman/claude-code-session-titles これ設定しといて

あとは Claude が下の手順で入れます。

## Claude Code 向けの設定手順

ユーザーからこのリポジトリの設定を頼まれた Claude Code は、次の手順で入れてください。

1. **hook を置く。** `hooks/session-title.py` を `~/.claude/hooks/session-title.py` に保存し、実行権限を付ける。

   ```bash
   mkdir -p ~/.claude/hooks
   curl -fsSL https://raw.githubusercontent.com/shoujiki-panman/claude-code-session-titles/main/hooks/session-title.py -o ~/.claude/hooks/session-title.py
   chmod +x ~/.claude/hooks/session-title.py
   ```

2. **`~/.claude/settings.json` に UserPromptSubmit hook を登録する。** 既存の設定は消さず、`hooks.UserPromptSubmit` の配列に次の1件を足す。`hooks` や `UserPromptSubmit` が無ければ作る。同じ `command` がすでに登録されていれば、何もしない。

   ```json
   { "hooks": [ { "type": "command", "command": "~/.claude/hooks/session-title.py" } ] }
   ```

   書き換えたあと、ファイルが JSON として読めることを確かめる。

   ```bash
   python3 -c "import json,os;json.load(open(os.path.expanduser('~/.claude/settings.json')));print('OK')"
   ```

   自分の設定ファイルの書き換えが権限の都合で止められた場合は、無理に回避しない。足す内容をユーザーに示し、ユーザー自身で `settings.json` に足してもらう。

3. **動くことを確かめる。** 試しの ID で1回目は指示が出力され、2回目は何も出力されないことを確かめてから、試しの印を消す。

   ```bash
   echo '{"session_id":"install-check"}' | ~/.claude/hooks/session-title.py | head -c 80; echo
   echo '{"session_id":"install-check"}' | ~/.claude/hooks/session-title.py | wc -c
   rm ~/.claude/hooks/state/session-title/install-check
   ```

4. **ユーザーに伝える。** 入れたことと、効くのは新しく開いたセッションからであることを伝える。頭の言葉を決めておきたい場合は、下の「頭の言葉を決める」を案内する。

Python 3 だけで動きます。追加のパッケージは要りません。

## 頭の言葉を決める

何も決めなければ、Claude が作業しているプロジェクトやリポジトリの名前を頭に付けます。調べものは「調べ」になります。

プロジェクトごとに決まった呼び名で揃えたいときは、`~/.claude/session-title-prefixes.txt` に1行に1つずつ書きます。空行と `#` で始まる行は読みません。

```
# 自分のプロジェクト
家計簿アプリ
ブログ
調べ
環境
```

ファイルを変えると、次の新しいセッションから反映されます。

## 今あるセッションも付け直す

hook が効くのは新しいセッションだけです。すでにあるセッションは、デスクトップアプリの Claude に頼めば付け直せます。

> 最近のセッションの題名を、会話の中身を読んで「プロジェクト名：中身」に付け直して

Claude がほかのセッションの会話を読み、題名を1件ずつ変えます。

## サイドバーの見方

題名の頭にプロジェクト名が付くと、サイドバーを「日付で区切る・最近動いた順」にしても、どのプロジェクトかが読めます。最後に作業したセッションが一番上に来ます（開いて見返しただけでは順番は変わりません）。今やるものはピン留めしておくと、日付の区切りより上に出ます。

## 調整

| 変数 | 既定 | 意味 |
|---|---|---|
| `SESSION_TITLE_PINS` | `on` | `off` にすると、ピンの付け替えを頼まない（題名だけ） |
| `SESSION_TITLE_PREFIX_FILE` | `~/.claude/session-title-prefixes.txt` | 頭の言葉のファイル |
| `SESSION_TITLE_STATE_DIR` | `~/.claude/hooks/state/session-title` | 「このセッションには指示済み」の印を置く場所 |

## テスト

```bash
python3 tests/test_session_title.py
```

## ライセンス

MIT
