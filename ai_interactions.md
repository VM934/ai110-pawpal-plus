# AI Interactions Log

## Agent Workflow (SF7)

**What task did you give the agent?**

Exact prompts used:

```text
Complete anything else that needs to be completed. Check both my personal and student email too for anything relevant.
```

```text
Did you check other projects feedback and carry that forward?
```

Working prompt I used after reading the prior feedback:

```text
Build PawPal+ so it follows the AI110 feedback from my last project: keep pure logic separate from Streamlit, include explicit boundary and edge-case tests, document exact prompts, keep the reflection specific, and make multiple meaningful commits.
```

**What did the agent do?**

- Checked course progress, emails, and prior AI110 feedback.
- Cloned the official PawPal+ starter repository.
- Removed a tracked Python bytecode file from the starter.
- Implemented `pawpal_system.py` with `Owner`, `Pet`, `CareTask`, `ScheduledTask`, `SkippedTask`, `DailyPlan`, and `PawPalScheduler`.
- Added `demo.py` as a CLI-first verification script.
- Added pytest coverage in `tests/test_pawpal_system.py`.
- Connected `app.py` to the backend scheduler.
- Updated `diagrams/uml.mmd`, `README.md`, and `reflection.md`.
- Ran `python -m py_compile`, `python demo.py`, and `pytest -q`.

**What did you have to verify or fix manually?**

- Verified that previous feedback emphasized modular logic, tests, exact prompt logging, and specific documentation.
- Fixed pytest import configuration by adding `pytest.ini`.
- Adjusted two tests after reviewing actual scheduler behavior: a flexible task should move after an occupied preferred slot, and equal-priority recurring tasks can be ordered deterministically by duration.
- Re-ran the full test suite until all tests passed.

## Prompt Comparison (SF11)

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | Codex agent | Codex agent |
| **Prompt** | `Complete the AI110 PawPal+ project.` | `Build PawPal+ so it follows the AI110 feedback from my last project: keep pure logic separate from Streamlit, include explicit boundary and edge-case tests, document exact prompts, keep the reflection specific, and make multiple meaningful commits.` |
| **Response summary** | Produced a broad plan but did not emphasize prior feedback or grader habits. | Produced a more targeted checklist: backend first, tests second, UI third, docs/reflection last. |
| **What was useful** | Fast starting point. | Better alignment with rubric and prior feedback. |
| **Problems noticed** | Too easy to miss exact prompt logging and edge-case tests. | Longer prompt, but more precise. |
| **Decision** | Not used as the final workflow. | Used as the final workflow. |

**Which approach did you use in your final implementation and why?**

I used Option B because the earlier project feedback already showed what graders value: modular code, meaningful tests, specific reflection, and a clear AI process record.
