# Operations

## Secrets
`secrets.env` (gitignored; template `secrets.env.example`): `PROLIFIC_TOKEN`, `JATOS_URL`
(`https://jatos.mindprobe.eu`), `JATOS_TOKEN` (JATOS → your name → My API tokens), `JATOS_STUDY_ID` (your study's numeric id).

## Local testing
```bash
scripts/serve_local.sh        # serves the repo root on :8000 (range requests for the video)
```
Open `http://localhost:8000/task/index.html?dim=anxiety&reset=1` (or `dim=affect2d`).
Local-only URL parameters: `reset=1` clears the saved session, `skip=intro` jumps to the film.
Any environment: `start_time=<s>` starts the film late (testing), `video=<url>` overrides the film,
`input=slider` (1D only).

Automated run-through (headless Chrome, Playwright; film starts at 795 s so a run takes ~2 min):
```bash
python tests/e2e_local.py --dim anxiety
python tests/e2e_local.py --dim affect2d
python tests/e2e_local.py --dim anxiety --reload          # reload mid-film, check resume
python tests/e2e_local.py --dim anxiety --live --base "$(cat prolific/jatos_link.txt)"   # against MindProbe
```
`--live` leaves a test result (`PROLIFIC_PID=TESTPID`) in JATOS – delete it before launch.

## Deploying to MindProbe (JATOS 3.11.3)
```bash
python scripts/deploy_jatos.py --check          # token, study, components, assets
python scripts/deploy_jatos.py                  # upload task/, create the component if missing
python scripts/deploy_jatos.py --video          # also upload media/towerClimb.mp4 (288 MB; already uploaded)
python scripts/deploy_jatos.py --link           # enable General Single links, write prolific/jatos_link.txt
```
Notes: the script resolves the study UUID and does not keep cookies (JATOS ignores the Bearer token once a
session cookie is sent). The component is reloadable (needed for resume). Config keys can be overridden without
redeploying via JATOS study properties → Study input (JSON), e.g. `{"videoUrl": "https://…/film.mp4"}`.

## Prolific
Settings: `prolific/study_template.json` (description, £4.80, 30 min, desktop only, completion codes) and
`prolific/filters.json` (fluent English, normal/corrected vision, approval ≥ 95%, ≥ 20 previous submissions).
Completion codes must match `task/js/config.js` (the script checks this):
`VMPDONE1` (completed → manual review) and `VMPNOCON` (no consent → request return).

```bash
python scripts/create_prolific_study.py --dim anxiety  --places 6 --tag pilot
python scripts/create_prolific_study.py --dim affect2d --places 6 --tag pilot --block <study-1-id>
```
This only creates **drafts** in the MovieRatings project. Preview in the Prolific web UI, then publish there
(or `scripts/prolific.sh study publish <id>`). Add Study 2 to Study 1's blocklist in the web UI too, so the
exclusion works in both directions. Avoid `prolific studies list` in scripts (it did not return in testing).

## Reviewing submissions
Completed submissions arrive as "awaiting review". For each, check the `summary` in the `final` line:
- **Rejection** (Prolific policy: only with clear evidence that the participant broke the study's terms; the task is
  off-platform, so Prolific's own authenticity checks do not apply and the evidence must come from our data):
  - `attention_checks_failed == 2`, or
  - clear evidence of AI or automated tools, which the consent forbids: e.g. `film_untrusted_events > 0`
    (script-generated input), mouse "teleporting" in the raw trajectory (`inputs.dx/dy`, `film_max_mouse_step_px`,
    implausibly regular movement), or a free-text answer with few/no keystrokes for its length. Document the evidence
    when rejecting.
  - Merely suspicious data -> exclude (pay), don't reject.
- **Demographics:** `scripts/prolific.sh study demographic-export <study_id>` (Prolific profile data: age, sex,
  first language, countries, student/employment status; returned submissions show "CONSENT REVOKED").
- **Data exclusion** (still pay): many interruptions/long `away_ms_total`, `practice_mae_last` high after the
  repeat, long flat-lined rating stretches, `seen_before`, `final_text_keystrokes` far below the character count,
  free text that reads as generated.
Approve/reject in the Prolific UI or with `scripts/prolific.sh submission …`.
