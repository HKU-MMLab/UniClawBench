# Outlook Web Login — Executor Notes

This file is visible to the executor. It is background context, not a
script.

## Where the credentials live

Inside the container:

```
/tmp_workspace/clawbench/.privacy/email_credentials.env
```

Gitignored on the host, injected at task start, file mode `0600`.
Treat it as sensitive.

Format (KEY=VALUE, comments start with `#`):

```
OUTLOOK_URL=https://outlook.live.com/mail/
EMAIL_ADDRESS=<outlook-address>@outlook.com
EMAIL_PASSWORD=<outlook password>
```

## Login paths you can use

Outlook accepts more than one web-login flow. Pick whichever works —
the task is graded by whether you **end up inside the inbox**, not by
whether the site showed the simple path or one of Microsoft's extra
account-check pages first.

1. Open Outlook Web
   - open `OUTLOOK_URL` (normally `https://outlook.live.com/mail/`)
   - if it lands on a Microsoft marketing page first, click `Sign in`
   - legitimate sign-in surfaces include `outlook.live.com`,
     `login.microsoftonline.com`, and `login.live.com`

2. Enter the email, then continue to the password path
   - type `EMAIL_ADDRESS`
   - some runs go directly to a password page
   - some runs first show a Microsoft verification page with a visible
     `使用密码` / `Use password` fallback; that path is valid and was
     observed in the reference run

3. Submit the password
   - type `EMAIL_PASSWORD`
   - after password submit, Microsoft may ask `保持登录状态?` /
     `Stay signed in?`; either answer is acceptable as long as you
     continue into the mailbox

Whichever path you take, the run is considered successful when you land
in the mailbox UI (e.g. `收件箱` / `Inbox` visible, `新邮件` / `New mail`
button present, Outlook header loaded, URL under `outlook.live.com/mail`).

## Saving evidence

Save everything under `/tmp_workspace/results/`:

- at least one screenshot of the logged-in inbox (confirms the primary outcome)
- a short status file (e.g. `login_status.txt` or `status.md`) with
  something like `status: success` or `status: failure` plus a one-line
  note — this is your claim, and the screenshot must back it

## Hygiene reminders

- Never write `EMAIL_PASSWORD` into any file under
  `/tmp_workspace/results/` — the supervisor scans visible artifacts
  for the exact string and caps the score at 0 if it finds a match.
- Never pass the password on a CLI (`--password=...`). Arguments show
  up in the runtime transcript.
- In the browser, the password field is normally masked. If a screenshot
  happens to contain the password in plaintext (e.g. due to a "show
  password" toggle), discard that screenshot before saving.
- Prefer reading the env file with Python (`open()` or `python-dotenv`)
  or via the browser snapshot's built-in form-fill, not shell `export`.

## What failure looks like

If you genuinely cannot log in (wrong password, Microsoft account check,
site unavailable, or Microsoft account check that you cannot resolve),
save the attempt evidence anyway:

- a screenshot of the error state
- a status file saying `status: failure` with a one-line reason

The supervisor prefers `continue` on a recoverable failure and only
`fail` when the run has exhausted retries with no path forward.
