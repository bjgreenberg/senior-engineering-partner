# Privacy Policy — senior-engineering-partner

Last updated: 2026-07-07 10:47 PM CDT

This policy covers the `senior-engineering-partner` plugin: the Agent Skill (`SKILL.md`),
its reference library (`references/`), its evaluation suite (`evals/`), and its helper
scripts (`scripts/`), however installed (Claude Code plugin marketplace, git clone, or any
other Agent-Skills-compatible tool).

## What the plugin collects: nothing

- The plugin is **static Markdown instructions** loaded locally by your AI coding
  assistant. It contains **no telemetry, no analytics, no usage tracking, no accounts, no
  cookies**, and it stores no personal data.
- It bundles **no MCP servers, no hooks, and no background processes** — its component
  inventory is exactly one skill.
- The skill itself makes **no network calls**. The optional helper scripts under
  `scripts/` (dependency audit, Mermaid render-check, citation validation, eval runner)
  run **only when you invoke them explicitly**, and contact only the standard developer
  services those tools require (for example, the OSV vulnerability database via
  `pip-audit`, a container registry for the pinned render image, or your local `claude`
  CLI). They transmit nothing else and report nothing back to the plugin's author.

## Your conversation and code

Prompts, code, and files you work on while the skill is loaded are processed by the AI
product you run it in — not by this plugin. That processing is governed by the product
vendor's own privacy policy (for Claude Code, see
[Anthropic's privacy policy](https://www.anthropic.com/legal/privacy)).

## Changes and contact

Changes to this policy land as ordinary commits to this file, so its full history is
auditable in git. Questions or concerns: open a
[GitHub issue](https://github.com/bjgreenberg/senior-engineering-partner/issues), or use
the maintainer contact in [`MAINTAINERS.md`](MAINTAINERS.md).
