---
name: enterprise-legal-guardrails
description: Enterprise-grade compliance and legal guardrails for outbound bot actions, with checks for anti-spam, policy risk, HR-sensitive language, privacy leakage, defamation risk, and financial claim controls.
---

# Enterprise Legal Guardrails

Use this skill to preflight bot output before posting, messaging, or publishing anything that could create legal/compliance risk.

## What it is
A generic **outbound** guardrail checker used by workflows before execute actions such as post/comment/message/chat/send in any app.

## When to use
- Before `create_post`, `create_comment`, `send_message`, or equivalent publish actions.
- Before market-related commentary, strategy claims, or price/certainty statements.
- Before HR-sensitive or workplace-adjacent messaging.
- Before anti-spam or coordination-heavy communications.
- Before handling or exposing personal identifiers.

## Workflow

1. Draft text.
2. Run the checker with the matching action/profile.
3. If result is **PASS/WATCH**, proceed.
4. If **REVIEW**, rewrite or route for human/legal review.
5. If **BLOCK**, do not execute.

Use it as a shared OpenClaw outbound safety layer for any skill that publishes content.
Babylon is only one current integration example, not the primary purpose of the skill.

## Quick usage

```bash
python3 scripts/check_enterprise_guardrails.py \
  --action post \
  --app <app_name> \
  --policies social antispam hr \
  --text "Draft text here"
```

```bash
python3 scripts/check_enterprise_guardrails.py \
  --action comment \
  --scope include \
  --apps whatsapp,telegram \
  --text "Draft text here"
```

```bash
python3 scripts/check_enterprise_guardrails.py \
  --action market-analysis \
  --text "Market commentary..." \
  --json
```

## App scope (global filtering)

Scope applies to any app-context passed with `--app` and these env vars (legacy names preserved for compatibility):

- `ENTERPRISE_LEGAL_GUARDRAILS_OUTBOUND_SCOPE` (`all|include|exclude`)
- `ENTERPRISE_LEGAL_GUARDRAILS_OUTBOUND_APPS` (comma-separated list)
- `BABYLON_GUARDRAILS_SCOPE`
- `BABYLON_GUARDRAILS_OUTBOUND_SCOPE`
- `BABYLON_GUARDRAILS_APPS`

Examples:

- `all`: check all outbound content.
- `include` + `whatsapp,email`: only check those apps.
- `exclude` + `whatsapp,email,moltbook,babylon`: everything except these apps.

If scope is omitted, default is `all`.

## Profiles

- `social`: public social text, comments, announcements.
- `antispam`: unsolicited/pumping/coordinating messaging.
- `hr`: workplace, hiring, performance, or employee conduct language.
- `privacy`: personally identifying data and private information disclosures.
- `market`: market/financial claims and outcome assertions.
- `legal`: legal conclusions/implication language.

If no profile is provided, defaults are derived from `--action`:
- `post|comment|message` → `social,legal`
- `trade|market-analysis` → `market,financial`
- `generic` → `legal,social`

## Output

- `PASS`: safe to execute
- `WATCH`: low risk; optional rewrite
- `REVIEW`: human/legal review recommended
- `BLOCK`: do not execute

## Compatibility

Legacy name `legal-risk-checker` is preserved in OpenClaw workspaces that still reference it.

## References

See `references/guardrail-policy-map.md` for the full policy rule set and suggested rewrites.

## Packaging

A distributable bundle is available at:
- `dist/enterprise-legal-guardrails.skill`
