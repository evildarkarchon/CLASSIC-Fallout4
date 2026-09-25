# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues in `evildarkarchon/CLASSIC-Fallout4` (`origin`). Use the `gh` CLI for all operations. From this checkout, `gh` resolves to that repository; pass `--repo evildarkarchon/CLASSIC-Fallout4` when working elsewhere.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. For a multiline body, write it to a file and use `--body-file <path>`.
- **Read an issue**: `gh issue view <number> --comments`. Use `--json number,title,body,labels,comments` when structured output is needed.
- **List issues**: `gh issue list --state open`, with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."` or `--body-file <path>`.
- **Apply or remove labels**: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`.
- **Close an issue**: `gh issue close <number> --comment "..."`.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs use the same labels and states as issues:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>`.
- **List external PRs for triage**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments`, retaining `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, and `NONE` author associations.
- **Comment, label, or close**: use `gh pr comment`, `gh pr edit`, and `gh pr close`.

GitHub shares one number space across issues and PRs. Resolve an ambiguous `#42` with `gh pr view 42`, then `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: an issue labelled `wayfinder:map` with the Notes, Decisions-so-far, and Fog body.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue using `gh api`. Where sub-issues are unavailable, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Use `wayfinder:<type>` labels (`research`, `prototype`, `grilling`, or `task`).
- **Blocking**: use GitHub issue dependencies. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where the database ID comes from `gh api repos/<owner>/<repo>/issues/<n> --jq .id`. Where dependencies are unavailable, use a `Blocked by: #<n>, #<n>` line in the child body.
- **Frontier**: inspect the map's open children in map order, skipping assigned children and those with open blockers. First eligible child wins.
- **Claim**: `gh issue edit <n> --add-assignee @me` before doing the ticket's work.
- **Resolve**: comment with the answer, close the child, then append a context pointer and link to the map's Decisions-so-far.
