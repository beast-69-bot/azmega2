# XWallet Flow Extraction Prompt

Use this prompt with another bot or model when you want it to reverse-engineer the XWallet flow from the source bot and map it into this leech bot.

Important:
- The source bot has both manual and `xwallet` payment branches.
- Focus on the `xwallet` branch only.
- Ignore the manual screenshot branch unless comparison is needed.
- If the target bot/model cannot access local paths, paste the relevant code from the source files below along with this prompt.

Verified source files:
- `C:\Users\anshu\OneDrive\Documents\telegram_selling_bot\bot\handlers\user\payment.py`
- `C:\Users\anshu\OneDrive\Documents\telegram_selling_bot\bot\services\xwallet_service.py`

Verified source behavior:
- `create_payment(amount)` creates the payment request.
- Gateway returns at least `qr_code_id` and `payment_link`.
- `payment_link` is sent to the user as a button.
- `qr_code_id` is stored and polled.
- `wait_for_payment(qr_code_id, timeout_minutes=5)` polls every 5 seconds.
- Success statuses:
  - `TXN_SUCCESS`
  - `SUCCESS`
  - `PAID`
  - `COMPLETED`
- Failure statuses:
  - `FAILED`
  - `TXN_FAILED`
  - `EXPIRED`
  - `CANCELLED`
- Success auto-marks the order as paid.
- Failure or timeout marks the order as expired.
- The `xwallet` branch is auto-verification based, not screenshot-based.

Copy and use this prompt:

```text
I want you to reverse-engineer an existing XWallet payment flow from a source Telegram bot and then map that same flow into my current Telegram leech bot.

My current bot context:
- It is a leech-focused Telegram bot.
- Main user commands are:
  /start
  /help
  /leech
  /qbleech
  /ytdlleech
  /btsel
  /cancel
  /status
  /usetting
- Admin/maintenance commands kept:
  /restart
  /log
  /cancelall
- I want payment to fit into this bot without breaking the leech-first UX.
- I want premium/free plan visibility in /status.
- I want the result to be implementation-ready, not generic.

Source XWallet flow already identified:
- `create_payment(amount)` is used to create a gateway payment request
- gateway returns at least:
  - `qr_code_id`
  - `payment_link`
- `payment_link` is sent to the user as a button
- `qr_code_id` is stored and used for polling
- `wait_for_payment(qr_code_id, timeout_minutes=5)` polls every 5 seconds
- success statuses:
  `TXN_SUCCESS`, `SUCCESS`, `PAID`, `COMPLETED`
- failure statuses:
  `FAILED`, `TXN_FAILED`, `EXPIRED`, `CANCELLED`
- if payment succeeds:
  - order is auto-marked paid
  - user gets confirmation
- if payment fails or times out:
  - order is marked expired
  - user gets expiry/failure notice
- this source XWallet branch is auto-verification based, not screenshot-based

Source files to analyze:
- `C:\Users\anshu\OneDrive\Documents\telegram_selling_bot\bot\handlers\user\payment.py`
- `C:\Users\anshu\OneDrive\Documents\telegram_selling_bot\bot\services\xwallet_service.py`

What I need from you:
1. Extract the exact source-bot XWallet flow.
2. Separate clearly:
   - observed from source
   - inferred from source
   - recommended adaptation for my bot
3. Then map that exact flow into my current leech bot.
4. Do not give generic payment architecture unless something is missing.
5. Be precise enough that another engineer can implement it directly.

Return the answer in this exact structure:

1. Source Flow Summary
- what command/button starts payment
- what order state exists before payment
- what gateway calls happen
- what user sees
- what gets stored
- what gets polled
- when order becomes paid / expired

2. Source Runtime Sequence
Give exact step-by-step runtime sequence:
- user action
- bot response
- gateway call
- stored fields
- polling loop behavior
- terminal outcomes

3. Gateway Contract
Document exact fields and behavior needed from XWallet:
- request params for payment creation
- expected create response fields
- expected status check response field(s)
- success statuses
- failure statuses
- timeout behavior
- retry/error fallback behavior

4. Source State Model
List exact state/data needed:
- order fields
- payment fields
- user entitlement fields
- timestamps
- message IDs / callback data if relevant

5. Integration Mapping For My Leech Bot
Map the source XWallet flow into my bot:
- where `/buy` or equivalent should fit
- where plan selection should happen
- how to preserve my existing `/leech`, `/qbleech`, `/ytdlleech` flow
- what premium fields should exist in my bot
- how `/status` should show:
  - Free
  - active plan label
  - expiry time
- what minimum DB/user_data fields are required
- what admin controls are required, if any

6. Implementation Spec
Give a decision-complete implementation spec:
- handlers needed
- service layer methods needed
- DB fields needed
- background polling behavior
- expiry behavior
- user messages
- edge cases
- acceptance criteria

7. Final Deliverables
At the end give:
- a compact flow diagram
- a list of commands/buttons/events
- a list of states/status values
- a minimal pseudocode outline for integration

Important constraints:
- I want the exact XWallet-style auto-payment flow, not manual screenshot approval, unless the source clearly mixes both.
- If the source contains both manual and xwallet branches, focus on the xwallet branch and explicitly ignore the manual branch except for comparison.
- Be explicit about what is source-truth vs what is your recommendation for my bot.
- Optimize for direct implementation, not theory.
```
