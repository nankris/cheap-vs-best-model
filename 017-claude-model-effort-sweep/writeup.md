# Haiku fixed every bug Opus did, for 1/30th of the price

*Draft. Tech in General experiment #017. 60 headless Claude Code runs, 2026-10-15 IST.*

Ten small JavaScript bugs, six setups: Haiku 5.5 at low/medium/high effort, Sonnet 5.5, and Opus 5.5 at default and low effort. Everything else identical.

**Every setup fixed all 10.**

| Setup | Cost per fixed bug |
|---|---|
| Haiku (any effort) | 0.36¢ |
| Sonnet | 5.0¢ |
| Opus (low or default) | 10.5–10.9¢ |

**Effort didn't matter.** Haiku on high wrote about 28% more tokens than on low and cost the same. Opus on low saved 4%.

**Haiku works differently.** It took a turn or two more and wrote about twice the output of the bigger models, but at its price that's noise. Time per task was ~10 seconds for all of them.

**The honest caveat.** These bugs are easy. The interesting question is where Haiku starts failing, and that needs harder tasks. But for "fix this small, well-described thing," paying for Opus is paying for nothing.

*$ are API-equivalent estimates from Claude Code's `total_cost_usd`; Pro isn't billed per token.*
