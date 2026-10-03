# ahao-learn-toolkit

「阿浩_Learn」视频里提到的提示词和 Skill。视频讲研究和方法，这里放能直接拿去用的部分。

Prompts and agent skills from the「阿浩_Learn」videos on learning, thinking and using AI well.

## 目录

| 目录 | 内容 | 怎么用 |
|---|---|---|
| `prompts/` | 每期一个提示词文件，文件名带期数 | 打开文件，复制全文，粘到你常用的 AI 对话里 |
| `skills/` | 可安装的 Agent Skill，每个是一个文件夹，含 `SKILL.md` | 见下方“安装 Skill” |

## 现有内容

| 文件 | 说明 | 对应视频 |
|---|---|---|
| [`prompts/02-让AI考你.md`](prompts/02-让AI考你.md) | 让 AI 出题考你，而不是替你总结 | 第 2 期 |
| [`skills/thinking-coach`](skills/thinking-coach/SKILL.md) | 思维教练：用思维模型一问一答引导你自己想清楚，含“学完自测” | 第 2 期 |

## 安装 Skill

一行命令安装（需要 Node.js）：

```bash
npx skills add https://github.com/1095327780/ahao-learn-toolkit
```

也可以手动安装：下载本仓库，把 `skills/` 下需要的文件夹复制到你的 Skill 目录，例如 Claude Code 的 `~/.claude/skills/`。

## 国内访问

国内镜像地址会在开通后写在这里。

## 许可

MIT，见 `LICENSE`。
