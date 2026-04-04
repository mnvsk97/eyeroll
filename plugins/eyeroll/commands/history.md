---
description: List past video analyses from the cache
argument-hint: '[clear] [--limit N] [--json]'
allowed-tools: Bash
---

Show past eyeroll analyses.

Raw arguments:
`$ARGUMENTS`

Run:

```bash
eyeroll history $ARGUMENTS
```

If the output shows past analyses, present them in a readable format.
If the user asks about a specific past analysis, they can re-watch the same video and it will use the cached intermediates (instant, no API cost).

If the user says "clear" or "clear cache":

```bash
eyeroll history clear --yes
```
