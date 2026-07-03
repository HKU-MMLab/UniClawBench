# Outlook Reference Trajectory — 2026-04-15

This hidden note records one successful local feasibility run for
`task_001_outlook_login`.

The raw authoring probe succeeded on 2026-04-15 and reached the Outlook
mailbox UI. This trajectory is a **reference for feasibility and target
resolution**, not the only acceptable execution path.

## Result

- Outcome: success
- Final URL shape: `https://outlook.live.com/mail/?deeplink=mail%2F`
- Final visible mailbox signals:
  - Outlook header loaded
  - `新邮件` / `New mail` button visible
  - `收件箱` / `Inbox` selected in the folder pane

## Observed Flow

1. Open Outlook web sign-in.
   - Hidden screenshot: `outlook_signin_email_prompt_2026-04-15.png`
   - Visible state: Microsoft sign-in page asking for the account email
2. Submit the account email.
   - Observed branch: the account did **not** go straight to password
   - Instead it showed a Microsoft `验证你的电子邮件` page with a visible
     `使用密码` fallback
   - Hidden screenshot: `outlook_signin_verification_branch_2026-04-15.png`
3. Click `使用密码`, then enter the password.
   - Hidden screenshot: `outlook_signin_password_prompt_2026-04-15.png`
4. After password submit, Microsoft showed `保持登录状态?`
   - Choosing `否` still led into the mailbox
   - Hidden screenshot: `outlook_signin_stay_signed_in_prompt_2026-04-15.png`
5. Mailbox loaded successfully.
   - Hidden screenshot: `outlook_mail_inbox_2026-04-15.png`

## Scoring Implications

- Do **not** require the executor to see a password box immediately after
  entering the email.
- The `验证你的电子邮件` branch is still recoverable and should normally
  score as `continue` if the executor has not yet taken the visible
  `使用密码` fallback.
- Do **not** grade against the exact inbox contents from the authoring run.
  Only the mailbox UI matters.
- The hidden screenshots are deliberately redacted. They are meant to
  anchor the flow and the UI shape, not to expose real mailbox contents.
