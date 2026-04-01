---
name: video-to-skill
description: >
  Watch a tutorial, demo, or walkthrough video and generate a Claude Code
  skill from it. Extracts the workflow, commands, tools, and patterns
  demonstrated and produces a SKILL.md with implementation. Supports
  Loom, YouTube, and local files.
---

# Video to Skill

Watch a tutorial, demo, or walkthrough video and generate a Claude Code skill from it.

## What This Skill Does

Given a video demonstrating a workflow, tool, or technique, this skill:

1. Analyzes the video to understand what's being demonstrated (via `eyeroll watch`)
2. Extracts: commands run, tools used, patterns followed, workflow steps
3. Identifies the core capability being shown
4. Generates a SKILL.md following the agent skills specification
5. Optionally scaffolds implementation scripts

## Setup

```bash
pip install eyeroll
eyeroll init          # set up Gemini API key
brew install yt-dlp   # for URL downloads
```

Or: `export GEMINI_API_KEY=your-key`

## When To Use This Skill

- User shares a video and says "create a skill from this"
- User shares a tutorial and wants to automate the workflow shown
- User says "watch this and make it into a skill/plugin/command"
- User shares a demo of a tool and wants a Claude Code skill that replicates it
- User wants to turn a screen recording of a manual process into an automated skill

## Workflow

```
1. Run: eyeroll watch <source> --context "create a skill from this" --verbose
2. Read the structured notes — identify:
   - What workflow/process is demonstrated
   - What commands/tools are used
   - What inputs does it take
   - What outputs does it produce
   - What are the trigger phrases (when should this skill activate)
3. Design the skill:
   - Name: concise, lowercase, hyphenated
   - Description: what it does and when to trigger
   - Instructions: step-by-step agent instructions
   - Setup: any dependencies or env vars needed
4. Generate SKILL.md following the agent skills spec
5. If the skill needs scripts, scaffold them
6. Validate: does the SKILL.md make sense? Are instructions clear?
```

## Example Interactions

User: "Watch this video on how to deploy to Fly.io and make a skill"
Steps:
1. `eyeroll watch <url> --context "create a deployment skill for Fly.io"`
2. Notes show: user runs `fly launch`, configures settings, runs `fly deploy`, checks status
3. Generate skill:
   - Name: `fly-deploy`
   - Trigger: user asks to deploy, mentions Fly.io
   - Instructions: check for fly.toml, run fly deploy, verify health
   - Setup: requires `flyctl` CLI
4. Write `skills/fly-deploy/SKILL.md`

User: "Turn this Loom into a skill for our release process"
Steps:
1. `eyeroll watch <loom-url> --context "create a skill for our release process"`
2. Notes show: user bumps version, updates changelog, creates tag, pushes, creates GH release
3. Generate skill that automates the full release workflow

User: "Watch how I set up a new microservice and make it repeatable"
Steps:
1. `eyeroll watch <video>`
2. Notes show: user creates directory, copies template, updates config, registers in service mesh
3. Generate a scaffolding skill that automates new service creation

## Rules

- Always run `eyeroll watch` first to understand the full workflow before generating the skill.
- Follow the agent skills specification for SKILL.md format:
  - `name`: max 64 chars, lowercase, hyphens only
  - `description`: max 1024 chars, describes what AND when
  - Body: clear instructions an agent can follow
- Keep SKILL.md under 500 lines. Move detailed reference material to separate files.
- The generated skill should be self-contained — an agent reading only the SKILL.md should understand what to do.
- Include example interactions showing realistic trigger phrases.
- Include setup instructions for any dependencies.
- If the video shows a complex multi-step process, break it into clear numbered steps.
- Ask the user to review the generated skill before finalizing — the video interpretation may miss nuances.

## SKILL.md Template

```markdown
---
name: {skill-name}
description: >
  {What this skill does and when to use it.}
---

# {Skill Name}

{One-liner description.}

## What This Skill Does

{2-3 sentences explaining the capability.}

## Setup

{Dependencies, env vars, installation steps.}

## When To Use This Skill

{Bullet list of trigger conditions.}

## Workflow

{Numbered steps the agent should follow.}

## Example Interactions

{2-3 realistic examples with user input and expected agent actions.}

## Rules

{Guardrails and constraints.}
```
