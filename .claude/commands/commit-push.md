# commit-push

Commit ALL changes in the working directory and push to remote, regardless of conversation context.

## Context Handling:
**IGNORE ALL PREVIOUS CONVERSATION CONTEXT** - This command should commit and push ALL uncommitted changes in the repository, not just those related to the current conversation or task.

## Steps:
1. Stage ALL changes (`git add -A`)
2. Commit all staged changes with a comprehensive message
3. Push to the current branch

## Commit Message Format:
- Analyze ALL changes in the repository using `git diff --cached`
- Create a message covering ALL modifications, not just recent discussion
- Use prefix like "Feat:", "Fix:", "Refactor:", "Docs:", "Test:" based on change type
- Be comprehensive about all changes across the entire repository
- Add the normal "Co-Authored by Claude Code" message at the end

## Important:
- Always check `git status` to see ALL uncommitted changes
- Review ALL changes with `git diff` to ensure comprehensive commit message
- Stage everything with `git add -A` to include all changes
- Push to the correct branch (classic-next is the main branch)
- This is a "commit everything" command - use when you want to save all work
