# commit-push

Commit all changes and push to remote, starting with ClassicLib repository if applicable.

## Steps:
1. Check if ClassicLib is a submodule or separate repository
2. If ClassicLib exists as separate repo, commit and push there first
3. Commit and push main CLASSIC-Fallout4 repository
4. Use descriptive commit messages based on the changes made
5. Push to the classic-next branch (or current branch)

## Commit Message Format:
- Use prefix like "Feat:", "Fix:", "Refactor:", "Docs:", "Test:" based on change type
- Be specific about what was changed
- Reference any related issues if applicable

## Important:
- Always check git status before committing
- Review changes with git diff to ensure accuracy
- Ensure all tests pass before pushing (if applicable)
- Push to the correct branch (classic-next is the main branch)