# commit-push

Commit all changes and push to remote, starting with ClassicLib repository if applicable.

## Steps:
1. Commit and push the main repository
2. Use descriptive commit messages based on the changes made
3. Push to the current branch

## Commit Message Format:
- Use prefix like "Feat:", "Fix:", "Refactor:", "Docs:", "Test:" based on change type
- Be specific about what was changed
- Reference any related issues if applicable
- Add the normal "Co-Authored by Claude Code" message at the end.

## Important:
- Always check git status before committing
- Review changes with git diff to ensure accuracy
- Ensure all tests pass before pushing (if applicable)
- Push to the correct branch (classic-next is the main branch)
