# Referrals: set-up (about 15 minutes, once)

People who work at a company offer to refer job seekers. Their offer shows on that company's jobs on
Radarak with their name, title and LinkedIn. Job seekers write to them on LinkedIn and send their CV there.
Radarak never sees the job seeker, their messages or their CV.

You approve every offer by hand, so fake referrers and "pay me for a referral" scams never go live.

## 1. Make the Google Form

Google Forms → new blank form, titled **Offer referrals on Radarak**. Add these questions **in this order**
(the order matters: the pipeline reads the columns by position):

| # | Question | Type | Required |
|---|---|---|---|
| 1 | Your full name (as on LinkedIn) | Short answer | yes |
| 2 | Company you work at | Short answer | yes |
| 3 | Your job title | Short answer | yes |
| 4 | Your LinkedIn profile link (linkedin.com/in/...) | Short answer | yes |
| 5 | Which areas can you refer for? | Checkboxes: Data & Analytics, AI & Machine Learning, Software Engineering, Mobile Development, QA & Testing, UI/UX Design, DevOps & Cloud, Security, ERP & CRM, Networks & Telecom, Product & Delivery, IT & Support, Embedded & Chip Design, Clients & Projects | no (empty = all) |
| 6 | Which levels can you refer? | Checkboxes: Intern & junior, Mid, Senior, Lead and above | no (empty = all) |
| 7 | Office location (city, country) or Remote | Short answer | no |
| 8 | Link to one specific job you can refer for | Short answer | no |
| 9 | A short note for job seekers (max 200 characters) | Short answer | no |
| 10 | Your work email (only to check you work there, never shown) | Short answer | yes |
| 11 | I refer for free and agree that my name, company, title and LinkedIn are shown on Radarak | Checkbox: I agree | yes |

Use the exact spelling of the options in 5 and 6.

Settings → Responses: turn off "Collect email addresses" (question 10 covers it).

## 2. Connect it to a sheet and add an Approved column

Responses tab → **Link to Sheets** → create a new spreadsheet. In the answers tab (usually
"Form responses 1"), click the first empty column header after the last question (column **M**),
type **Approved**, then select that column and Insert → **Checkbox**.

## 3. Make the public tab

Add a new tab named **Published**. In cell A1 paste (change the tab name if yours is different):

```
=QUERY('Form responses 1'!A:M, "select A,B,C,D,E,F,G,H,I,J where M = TRUE", 1)
```

This tab shows only approved offers and never the work email (column K) or the agreement (L).

## 4. Publish only that tab as CSV

File → Share → **Publish to web** → in the first menu choose **Published** (not "Entire document"),
in the second choose **Comma-separated values (.csv)** → Publish → copy the link.

## 5. Add both links to `.env`

```
REFERRALS_FORM_URL=<the form's "Send" link, e.g. https://forms.gle/...>
REFERRALS_CSV_URL=<the CSV link from step 4>
```

Then `docker compose up -d`. From the next run, the site shows the "Offer to refer people" button and
every approved offer.

## Every day

* New offer in the sheet → check that the LinkedIn profile is real and the work email matches the company
  → tick **Approved**. It goes live on the next run.
* To remove someone: untick Approved (or delete the row). Offers older than 90 days drop off by themselves;
  the referrer can fill in the form again to renew.
* "Report" clicks show in GoatCounter as `report-referral/<id>`.
