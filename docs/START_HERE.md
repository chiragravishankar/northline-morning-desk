# Nothing Slips Through

*A product challenge presented by Peri · NYU Product Management Club × Base44 · Monday, Nov 16, 5–8 PM*

## The business

**Northline Supply** is a 40-person supplier in Secaucus, New Jersey. It buys from 48 manufacturers and sells takeout packaging, cleaning, kitchen and breakroom supplies to about 140 restaurants, cafés, offices, hotels and schools across New York City. Sales are about $1.2 million a month.

## The problem

Northline's data lives in places that don't talk to each other:

- **Delivery log:** every order that left the warehouse, and what actually arrived
- **QuickBooks:** customer invoices, credit memos and supplier bills
- **Price list and contracts:** list prices, customer price tiers, contract prices
- **Purchasing:** purchase orders and what arrived at the dock
- **Shared inbox:** emails from customers and suppliers, plus internal notes

Dana, the operations manager, keeps it all in her head. Even so, money slips through the cracks every month.

## Your challenge

Build the app Dana opens every morning. It should:

1. **Bring the data together** in one place.
2. **Catch what slipped.** For example:
    - orders delivered but never invoiced
    - an old price used after a price increase
    - a delivery fee billed twice
    - a customer billed for 10 cases when only 8 arrived
    - a supplier charging more than the agreed price
    - a customer email that never got an answer
    - a fake "we changed our bank details" email

    These are only examples. There are about 20 kinds of problems in the data.

3. **Show the proof.** Every flag links to the records behind it.
4. **Help her act.** Draft the catch-up invoice, credit or reply, and let Dana approve it before anything goes out.

## How to build it

```
data/*.csv ─► your code ─┬─► findings.csv ─► Base44 Findings table, and you submit it
                         └─► evidence.csv ─► Base44 Evidence table
```

1. **Your AI coding tool does the data work.** Use Claude Code, Codex, Cursor, or Claude/ChatGPT with file analysis. Your code reads the data, applies `billing_rules.md`, and writes two files:
    - `findings.csv`: one row per problem
    - `evidence.csv`: the records behind each problem

    Keep it as code you can re-run, because you'll run it again on October.

2. **Base44 is the app Dana uses.** Import the two files as tables. In the app, Dana works through her queue, checks the proof, and approves or dismisses each fix.

3. **You submit `findings.csv`.** It's the same file your app loads, so the app and your submission always agree.

`FINDINGS_AND_EVIDENCE.md` explains every column, with examples, and covers the 7 PM refresh. Blank templates and filled-in examples are in `templates/`.

## What to build in Base44

Your app uses three tables:

| Table | Comes from |
|---|---|
| **Findings** | Import `findings.csv` |
| **Evidence** | Import `evidence.csv` |
| **Decisions** | Made in the app as Dana works: status, reason, the draft, who and when |

It must do four things:

1. **Today's queue.** Every open finding, biggest dollars first, with a status: new, approved or dismissed. Group findings by their `cause`. For example: "Customer X is billed at the old tier: 77 invoice lines, $1,641."
2. **Proof.** Click a finding to see its Evidence rows: the delivery line, the invoice line, the price or rule that applies, and the math.
3. **Action.** One click drafts the fix: a catch-up invoice, a credit memo, a customer reply, a supplier dispute or a payment hold. Dana edits it and approves it, or dismisses the finding with a reason. Save the result in Decisions. Nothing goes out without her approval.
4. **What changed.** After October loads, show what's new, what's still open and what got fixed.

How it looks, and anything beyond these four, is up to you. That is what Product sense scores.

**Rules for the app**

- Load your two output files, not the raw data files.
- The totals your app shows must match your `findings.csv`. They will if the app loads the same file you submit. Judges check.
- Use Base44's AI to draft and explain, not to work out amounts.
- Don't send real emails. The data is fictional, but some email addresses could belong to real people. Drafts stay inside the app.

## The twist

At **7:00 PM** we release October's files. Re-run your code on both months. In Base44, clear the Findings and Evidence tables and import the new files, but keep Decisions. Then show Dana what's new, what's still open and what got fixed. The best teams do it without rebuilding anything. We're looking for a tool that keeps watching, not a one-time report.

## What's in this kit

| File | What it is |
|---|---|
| `START_HERE.md` / `Challenge-Brief.pdf` | This brief |
| `billing_rules.md` | **Read this first.** Northline's rules decide what "correct" means. |
| `DATA_DICTIONARY.md` | The nine data files, every column, and how the files connect |
| `FINDINGS_AND_EVIDENCE.md` | The two files your code writes, how they feed Base44, and how to submit |
| `templates/` | Blank `findings.csv` and `evidence.csv`, plus filled-in examples |
| `data/september/` | September's data: 9 CSV files |

All companies, people and numbers are fictional.

## What to submit by 7:30 PM

Everything goes through the event site (the link is on screen at kickoff). Sign in with a team name and a PIN, then:

1. **Paste the link to your Base44 app.**
2. **Upload your `findings.csv`**, covering September and October. Submit as often as every 10 minutes; your latest file counts.

The site shows your Catch score, and a live leaderboard runs on the big screen. It freezes at 7:15 PM, and the final scores are revealed at the end.

## Judging

| Weight | What we look at |
|---|---|
| **30% Catch** | How many of the planted problems and dollars you found. Scored automatically from your findings file. Flagging things that are correct under the rules costs points. |
| **20% Proof** | Your numbers come from code run on the data, not from AI guessing. Every flag in your app shows its records, and the app's totals match your findings file. Be ready to show the code. |
| **20% Action** | In your Base44 app, one click takes Dana from a finding to a draft invoice, credit, reply, dispute or payment hold. She approves it, or dismisses the finding with a reason. |
| **30% Product sense** | Would Dana use it every day? Biggest dollars first, findings grouped by cause, a clear view of what changed in October, and a clear reason for what you chose not to build. |

## Schedule

| Time | What |
|---|---|
| 5:00–5:10 | Welcome and case kickoff |
| 5:10 | Build |
| 5:30–6:30 | **Dana's desk:** interview Dana, 3 minutes per team |
| 6:30–7:30 | Judges walk the room |
| 7:00 | October's files released, and Dana has a new request |
| 7:15 | Leaderboard freezes |
| 7:30 | Submissions close |
| 7:40–7:55 | Finalist demos, 3 minutes each |
| 7:55 | Final board revealed, winners announced |

## Tips

- Read `billing_rules.md` before you build anything. Some things that look wrong are correct.
- Don't paste the files into a chat and ask for the answers. Have your coding tool write the checks as code, so the numbers are exact and you can re-run them on October.
- One row per record: if one cause hits 30 invoice lines, `findings.csv` gets 30 rows with the same `cause`.
- Load only your two output files into Base44. The raw files are bigger than a single Base44 request can return (5,000 records).
- In October, the transaction files add to September's, and the master files (customers, contract prices, products, suppliers) replace September's.
- Split the team early: someone on the data, someone on the Base44 app.
- Talk to Dana. She knows things that aren't in the data.
