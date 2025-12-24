# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a Claude Code marketplace plugin repository containing skills for the fzymgc-house self-hosted cluster. Skills are reusable prompts and workflows that extend Claude Code's capabilities.

## Structure

```
.claude-plugin/
  marketplace.json    # Plugin metadata (name, version, owner)
<skill-name>/
  SKILL.md           # Skill definition (required)
  *.md               # Additional skill resources
```

## Creating Skills

Each skill is a directory containing at minimum a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-name
description: Brief description for skill discovery
---

# Skill content and instructions
```

Skills should be self-contained and focused on specific tasks related to the fzymgc-house infrastructure.

## Planned Skills

- `grafana/` - Grafana dashboard and alerting management for the self-hosted cluster
