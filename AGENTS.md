# BatteryFlex engineering instructions

- Work on one task at a time; finish checks, update `docs/CURRENT_HANDOFF.md`, then stop for review.
- Inspect Git before editing. Preserve unrelated work. Use `codex/` feature branches for
  future changes; never commit directly to main or stage unrelated parent-project files.
- Use typed, focused Python modules under `src/batteryflex`; keep Streamlit in `ui/`.
- Add focused tests for implemented behaviour. Run `python -m pytest`,
  `python -m ruff check .` and `python -m ruff format --check .` before handoff.
- Turso is the default application read source. No implicit imports, startup writes,
  auto-migrations or fallback downloads. Validate imports and record provenance explicitly.
- Preserve NESO event dates and original 2013 household timestamps. Cross-period alignment
  is a documented simulation mapping, never a claim of contemporaneous observations.
- Separate historical observations, simulated battery configurations and run outputs.
- Never commit credentials, `.env`, local datasets or outputs. Never log auth tokens.
- Avoid speculative frameworks, empty service layers and fake optimisation results.
