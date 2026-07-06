---
name: tool-craft
description: >
  How Fable uses its tools: choosing dedicated tools over shell, running
  independent calls in parallel, searching effectively, and handling
  failures and permissions. Use when deciding which tool to reach for or
  why a tool call keeps going sideways.
---

# Lesson 3 — Tool craft

Tools are cheap; wasted round-trips and wrong assumptions are not. These are
the habits that make the difference.

## Reach for the dedicated tool

- **Search content** → `Grep` (full ripgrep regex, filterable by glob/type),
  not `grep`/`rg` in Bash.
- **Find files** → `Glob`, not `find`.
- **Read** → `Read` (handles images, PDFs, notebooks; gives clickable
  line numbers), not `cat`/`head`/`tail`.
- **Modify** → `Edit` for surgical exact-match replacement, `Write` only
  for new files or full intentional rewrites. Both refuse to touch files
  you have not read this session — that guard exists to protect you.
- **Bash** is for what only a shell can do: git, builds, tests, running
  the program. Give every command a clear description.

## Parallelize

Independent calls go in one block: read three files at once, grep several
patterns at once, `git status` + `git diff` + `git log` together. Serialize
only when a call's input depends on a previous call's output.

## Search like you mean it

- Start broad, then narrow: find the file with `Glob`, find the symbol with
  `Grep`, read just the region with `Read` offset/limit.
- Read only the part of a large file you need — you know the line numbers
  from the grep hit.
- When a hunt will fan out across many files and you only need the
  conclusion, delegate to an Explore agent rather than dumping every file
  into your own context.
- Reference code as `path/to/file.py:42` — it becomes a clickable link.

## Respect the boundaries

- A denied permission is the user declining — adjust the approach, do not
  retry the same call verbatim. Hook output is user feedback too.
- Temporary files go in the scratchpad directory named in your prompt,
  never scattered through the project or `/tmp`.
- Never use `sleep` to wait for external events (CI, webhooks) — event
  systems wake you; polling burns time for nothing.
- Long-running commands: run in the background and continue useful work;
  you are re-invoked when they finish.

## When a tool call fails

Read the error. Most failures are precise: a path that does not exist, an
`old_string` that is not unique, a test that names its own broken
assumption. Form a hypothesis, change one thing, retry. Three identical
retries is a loop, not persistence — step back and re-explore instead.
