#!/usr/bin/env python3
"""Turn a skill folder into things that can be shared on platforms that allow no links or files.

For 抖音 / 小红书 / 视频号 we can only post text (and images, and on 小红书 sometimes a PDF), so a
multi-file skill is packed into:

  安装命令.txt     one line, no domain:  npx skills add <owner>/<repo> --skill <name>
  安装提示词.txt    every file's path and full text, plus instructions, so an AI agent can rebuild the folder
  安装说明.pdf      the same text laid out for reading / the 小红书 file attachment (needs Chrome)

    python3 site/pack_skill.py procrastination-coach                 # writes to dist/packs/<name>/
    python3 site/pack_skill.py procrastination-coach --out somewhere/ --pdf
"""
import argparse
import html
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "1095327780/ahao-learn-toolkit"  # change here after the repo moves to the ahao-learn organisation
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts", ".sh", ".csv", ".html", ".css", ".toml"}
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LONG_POST_LIMIT = 8000  # 抖音长文上限（2025-12 媒体报道）


def skill_title(text, name):
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else name


def collect(src):
    files, skipped = [], []
    for f in sorted(src.rglob("*")):
        if not f.is_file() or f.name == ".DS_Store":
            continue
        rel = f.relative_to(src).as_posix()
        if f.suffix.lower() in TEXT_SUFFIXES:
            files.append((rel, f.read_text(encoding="utf-8")))
        else:
            skipped.append(rel)
    # SKILL.md first, the rest in path order
    files.sort(key=lambda x: (x[0] != "SKILL.md", x[0]))
    return files, skipped


def install_prompt(name, title, files):
    listing = "\n".join(f"- {rel}（{len(body)} 个字符）" for rel, body in files)
    blocks = "\n\n".join(f"<<<文件开始 {rel}>>>\n{body.rstrip(chr(10))}\n<<<文件结束 {rel}>>>" for rel, body in files)
    return f"""请帮我安装一个 Agent Skill：「{title}」（文件夹名 {name}）。

做法：
1. 在你的 Skill 目录里新建文件夹 {name}。Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/；其他工具用它自己的 Skill 目录，不确定就先问我。
2. 按下面的路径逐个建文件。每个文件的内容在“<<<文件开始 路径>>>”和“<<<文件结束 路径>>>”两行之间（这两行本身不写进文件）。必须逐字照抄：不改写、不省略、不补充、不调整格式。
3. 建完以后用 LC_ALL=en_US.UTF-8 wc -m 核对每个文件的字符数（允许末尾多一个换行），再告诉我结果。应该有 {len(files)} 个文件：
{listing}

{blocks}
"""


def write_pdf(text, title, out_pdf):
    if not Path(CHROME).exists():
        print("Chrome not found; skipped the PDF")
        return False
    page = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{html.escape(title)} 安装说明</title>
<style>
@page {{ size: A4; margin: 16mm 14mm; }}
body {{ font: 10.5pt/1.65 -apple-system, "PingFang SC", "Noto Sans CJK SC", sans-serif; color: #1F1A15; }}
h1 {{ font-size: 18pt; margin: 0 0 4mm; }}
.meta {{ color: #6F6255; margin: 0 0 6mm; }}
pre {{ white-space: pre-wrap; word-break: break-word; font: 9.5pt/1.6 "SF Mono", Menlo, monospace; margin: 0; }}
</style></head><body>
<h1>{html.escape(title)}：安装说明</h1>
<p class="meta">阿浩_Learn · AI 时代的成长说明书。把下面整段复制给 Claude Code、Codex 这类 AI agent，它会把 Skill 的文件建好。</p>
<pre>{html.escape(text)}</pre>
</body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page.html"
        src.write_text(page, encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={out_pdf}", src.as_uri()],
                       check=True, capture_output=True, timeout=120)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="folder name under skills/")
    ap.add_argument("--out", help="output folder (default dist/packs/<name>)")
    ap.add_argument("--pdf", action="store_true", help="also print 安装说明.pdf with Chrome")
    args = ap.parse_args()

    src = ROOT / "skills" / args.name
    files, skipped = collect(src)
    title = skill_title(dict(files).get("SKILL.md", ""), args.name)
    out = Path(args.out) if args.out else ROOT / "dist" / "packs" / args.name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    command = f"npx skills add {REPO} --skill {args.name}"
    (out / "安装命令.txt").write_text(command + "\n", encoding="utf-8")
    prompt = install_prompt(args.name, title, files)
    (out / "安装提示词.txt").write_text(prompt, encoding="utf-8")
    pdf = args.pdf and write_pdf(prompt, title, out / "安装说明.pdf")

    print(f"{args.name}: {len(files)} 个文件，安装提示词 {len(prompt)} 字符 → {out}")
    if len(prompt) > LONG_POST_LIMIT:
        print(f"  超过抖音长文上限 {LONG_POST_LIMIT} 字：在抖音要另做精简版，或者只给安装命令")
    if skipped:
        print(f"  这些不是文本文件，没法放进提示词，只能走 zip 或安装命令：{', '.join(skipped)}")
    if pdf:
        print("  已生成 安装说明.pdf")


if __name__ == "__main__":
    main()
