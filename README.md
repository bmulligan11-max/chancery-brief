# Chancery Brief — daily build with Claude

Files: `build.py` (the script), `template.html` (page design), `requirements.txt`,
and `.github/workflows/daily.yml` (the daily schedule).

## One-time setup

1. **Get an API key.** On the Claude Platform (platform.claude.com) add a few dollars of credit
   and create an API key. Copy it.
2. **Create a GitHub repository** (private is fine) and upload all four items,
   keeping the `.github/workflows/daily.yml` folder path.
3. **Add your key as a secret.** In the repo: Settings > Secrets and variables > Actions >
   New repository secret. Name it `ANTHROPIC_API_KEY` and paste the key.
4. **Turn on the website.** Settings > Pages > Build and deployment > "Deploy from a branch",
   branch `main`, folder `/docs`, then Save.
5. **Run it once by hand.** Actions tab > "Daily Chancery Brief" > Run workflow.
   When it finishes (a few minutes), your site appears at the address shown in Settings > Pages.
6. **From then on it runs by itself** every day at 22:30 UTC (06:30 Beijing).
   Change the time in `daily.yml` (the `cron` line).

## Your own domain (later)

In Settings > Pages add your custom domain, then point your domain's DNS at GitHub as the
page there instructs.

## What each run does

- Searches the web through Claude, builds `docs/index.html`, a dated copy in `docs/archive/`,
  and `docs/newsletter.md` (plain text to paste into an email tool).
- Removes any link Claude cites that it did not actually retrieve, and refuses to publish if
  fewer than three verified items remain (the previous page simply stays up).
- Prints the token and search usage and an estimated cost in the run log.
- Skips quietly if today's page already exists, so a re-run costs nothing.

## Keeping costs low

- Default model is `claude-haiku-5-5` and 8 searches a day. Expect roughly $0.10 a day
  (about $3 a month), most of it the $0.01-per-search fee. These are estimates; check the log.
- To change the model or search count without editing code: Settings > Secrets and variables >
  Actions > Variables, then add `CLAUDE_MODEL` (for example `claude-sonnet-5-5`) or `MAX_SEARCHES`.
- Haiku's low price applies to prompts up to 100K tokens; above that it is billed at 5x.
  Keep `MAX_SEARCHES` at 8 or below. The log warns you if a run gets close.

## Review before publishing (optional)

Automatic publishing has no human check. To review first, run locally:
`python build.py --draft`, open `draft/index.html`, then `python build.py --publish`.
