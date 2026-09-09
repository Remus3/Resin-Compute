---
name: Bug report
about: Something behaves differently from what the docs or the tests say
title: ''
labels: bug
assignees: ''
---

<!--
SECURITY ISSUES DO NOT GO HERE. Use the private route in SECURITY.md:
the repository's Security tab, then "Report a vulnerability".
-->

## What happened

<!-- What you observed. Paste the actual output rather than describing it. -->

## What you expected instead

<!-- And where that expectation came from - a doc, a test, a docstring. Naming
     the source helps, because sometimes the doc is the thing that is wrong. -->

## How to reproduce

1.
2.
3.

Smallest input that still triggers it, if you found one:

## Environment

- Commit or branch:
- Python version (`python --version`):
- Operating system:
- Path of the checkout contains a space: yes / no
- Hooks installed (`python scripts/install_hooks.py` has been run): yes / no / not sure

## Gate output

If a suite is involved, paste the command and its result rather than a summary.

```
python -m pytest tests
python -m pytest agents/pity_engine
```

<!-- Note: the two suites are run SEPARATELY. `pytest .` from the repository
     root is not supported and its failures are not bugs. -->

## Anything else

<!-- Log lines, a stack trace, what you already ruled out. Please redact
     absolute paths that contain your account name, and never paste a real
     credential or a real account identifier. -->
