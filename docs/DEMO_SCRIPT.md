
```markdown
# path: docs/DEMO_SCRIPT.md

# PolicyLens Sprint 7 demo script

This demo is a multi-surface proof. The goal is showing reviewer and customer surfaces behaving consistently, and showing pagination on page 2 as an explicit validation step. Evidence export is included as the audit-grade finish, and it is validated as both JSON and PDF.

The quickest path is running the demo shell script, because it seeds deterministic records and prints a claim id you can use for export checks. A manual path is included so the demo remains understandable even when run without automation.

## Automated path

Run the demo script from the repository root.

```bash
bash scripts/demo.sh