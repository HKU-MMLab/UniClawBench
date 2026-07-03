# Hidden Evaluation Rule — Outlook web login

## 1. Grading Philosophy

Graded by **outcomes**:

- Did the executor reach a legitimate Outlook / Microsoft sign-in page?
- Did it submit the right account from the credentials file?
- Did it end up in the logged-in Outlook mailbox UI?
- Did it save a screenshot of that logged-in state plus a short
  status file?
- For this smoketest, judge only completion and evidence quality. Do
  not use password leakage as a scoring dimension here.

Process-level variation is fine. The executor may see:

- an Outlook marketing page first, then click `Sign in`
- a `login.microsoftonline.com` email-entry page
- a `login.live.com` password page
- a Microsoft `验证你的电子邮件` / `Verify your email` branch with a
  visible `使用密码` / `Use password` fallback
- a `保持登录状态?` / `Stay signed in?` prompt after password submit

The executor is **not** penalized for:

- minor retries
- landing on a Microsoft sign-in surface instead of a pure Outlook page
- using the visible `使用密码` / `Use password` fallback to reach the
  password step
- answering the `保持登录状态?` prompt either way, as long as the run
  reaches the inbox

## 2. Task Contract (for reference)

The public task asks the executor to:

1. Read the credentials file at
   `/tmp_workspace/clawbench/.privacy/email_credentials.env`
2. Open Outlook Web in the browser
3. Log in with the email address + password from that file
4. Land in the inbox UI
5. Save, under `/tmp_workspace/results/`:
   - a screenshot of the logged-in inbox
   - a short status file stating success or failure
6. The public task also asks the executor not to expose the password,
   but for this hidden rule that is **not** part of the scoring rubric.

## 3. Inputs Available To You (supervisor)

Your Codex workspace mirrors the container's `.privacy/`:
`privacy/email_credentials.env` holds the real credentials (minus
redaction rules). The file has:

- `OUTLOOK_URL` (normally `https://outlook.live.com/mail/`)
- `EMAIL_ADDRESS`
- `EMAIL_PASSWORD`

Use it only to confirm that the executor's visible evidence is consistent
with the real account. Do **not** restate the password in your rationale
or missing_artifacts.

## 4. Feasibility Reference Run

A successful hidden authoring run was recorded on 2026-04-15.

Observed sequence:

1. Microsoft email-entry page
2. `验证你的电子邮件` branch
3. visible `使用密码` fallback
4. password page
5. `保持登录状态?` prompt
6. Outlook inbox

See:

- `outlook_reference_trajectory_2026-04-15.md`
- the redacted screenshots listed in Section 9

This run proves the task is feasible with the local credentials. It does
**not** make that exact click path mandatory.

## 5. Checkpoint Rubric

| ID | What matters (outcome) | Weight |
| --- | --- | --- |
| CP1 | The executor reached a legitimate Outlook / Microsoft sign-in surface in the browser (`outlook.live.com`, `login.microsoftonline.com`, `login.live.com`, Outlook mailbox URLs, etc.). Evidence can be a visible URL in transcript, browser snapshot, or saved screenshot. | 0.10 |
| CP2 | The visible evidence is consistent with the account from `email_credentials.env`. This can be shown either before login (matching email entered) or after login (mailbox UI shows the matching account). | 0.15 |
| CP3 | **The executor landed in the logged-in Outlook mailbox UI.** This is the primary outcome. Evidence = a screenshot (saved to `results/`) showing unambiguous mailbox signals such as `新邮件` / `New mail`, selected `收件箱` / `Inbox`, Outlook header, or similar. | 0.45 |
| CP4 | Artifacts are saved coherently under `results/`: a short status file plus at least one saved screenshot. For a successful run this should be an inbox screenshot; for a genuine failed attempt it can be the visible failure state plus a matching failure status note. | 0.20 |
| CP5 | The saved artifacts are auditable: the saved screenshot / status note is consistent with the claimed login state. Do not award or deduct points here based on password leakage. | 0.10 |

Total full score: `1.00`.

## 6. Scoring Policy

Apply the checkpoint weights above. Caps:

- cap at `0.50` if the executor never reaches the logged-in mailbox UI
  (stopped at sign-in page, verification branch, wrong-password page,
  stay-signed-in loop, or other pre-inbox state)
- cap at `0.30` if the executor used an account that does **not** match
  the one in `email_credentials.env`
- cap at `0.30` if the executor went to a clearly unrelated non-Microsoft
  mail domain instead of continuing the Outlook login flow
- cap at `0.80` if the executor reaches the inbox but does not save both
  a status file and a supporting screenshot under `results/`

Pass requirements (`score >= 0.95` → `verdict = pass`):

- CP3 satisfied (mailbox UI visible in a saved screenshot)
- CP4 satisfied (status file + screenshot both saved to `results/`)
- no other score cap above fired

## 7. Continue vs Fail Guidance

Prefer `continue` when:

- the executor opened the login page but has not yet submitted credentials
- the executor submitted the email and is now on the `验证你的电子邮件`
  branch but has not yet used the visible `使用密码` fallback
- the executor submitted the password and is now at `保持登录状态?`
  or another Microsoft post-login prompt that may still lead to the inbox
- the executor reached the inbox but hasn't saved a screenshot or status
  file yet
- login genuinely failed (wrong password, service unavailable, Microsoft
  account check unresolved) and the executor has budget left to retry —
  but do not demand more retries past the second follow-up

Prefer `fail` when:

- the executor used an account that doesn't match `email_credentials.env`
- the executor saved a screenshot that clearly shows the **logged-out**
  page but claims success in the status file (false-claim check)
- after all follow-ups, there is still no evidence of reaching the inbox
  and no realistic recovery path

## 8. Dynamic Content Note

Mailbox contents, unread counts, ads, and UI language may change between
the hidden reference run and the actual attempt. Judge CP3 against
generic Outlook mailbox signals, not against specific emails from the
reference run.

## 9. Hidden Reference Assets

- `outlook_reference_trajectory_2026-04-15.md`
- `outlook_signin_email_prompt_2026-04-15.png`
- `outlook_signin_verification_branch_2026-04-15.png`
- `outlook_signin_password_prompt_2026-04-15.png`
- `outlook_signin_stay_signed_in_prompt_2026-04-15.png`
- `outlook_mail_inbox_2026-04-15.png`

All screenshots are intentionally redacted to avoid exposing real mailbox
content while still anchoring the UI shape.

## 10. Notes For Rationale

- Do not restate `EMAIL_PASSWORD` in `rationale` or
  `missing_artifacts`, even though password leakage is non-scoring in
  this hidden rule.
- The account email itself is OK to name in `missing_artifacts` if you
  need to flag a mismatch.
- Guidance tags: `check_correct_source_page`, `save_visible_evidence`.
