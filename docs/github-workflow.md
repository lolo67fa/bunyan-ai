# GitHub Workflow Guide

A beginner-friendly guide to how the BUNYAN AI team uses Git and GitHub.

## The Golden Rules

1. **Never commit directly to `main`.** All changes go through a Pull Request.
2. **Work on your own branch** and on your own files.
3. **Pull `main` often** to stay up to date.
4. **Never commit secrets** — no API keys, passwords, or `.env` files.
5. **Ask before editing someone else's files**, and agree on shared JSON schemas before implementing them.

---

## 1. One-Time Setup

```bash
# Set your name and email (use the email linked to your GitHub account)
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# Clone the repository
git clone https://github.com/lolo67fa/bunyan-ai.git
cd bunyan-ai
```

## 2. Branch Naming Conventions

Each member has a main feature branch:

| Member | Branch |
|---|---|
| Ghala | `feature/ghala-analyst` |
| Jood | `feature/jood-project-manager` |
| Yara | `feature/yara-developer` |
| Sara | `feature/sara-qa` |
| Naifah | `feature/naifah-architect` |
| Alanoud | `feature/alanoud-backend` |

For smaller, short-lived pieces of work you can also use:

| Type | Pattern | Example |
|---|---|---|
| New feature | `feature/<name>-<topic>` | `feature/yara-validation` |
| Bug fix | `fix/<name>-<topic>` | `fix/sara-update-test` |
| Documentation | `docs/<topic>` | `docs/api-contract` |
| Project setup | `setup/<topic>` | `setup/project-foundation` |

Use lowercase letters and hyphens only.

## 3. Starting Your Work

```bash
# Make sure you have the latest main
git checkout main
git pull origin main

# Create your branch (first time only)
git checkout -b feature/<your-branch>

# Or switch to it if it already exists
git checkout feature/<your-branch>
```

## 4. Working with Issues

- Every task should have a **GitHub Issue** (repository → *Issues* → *New issue*).
- Include: a clear title, a short description, what "done" looks like, the assignee, and labels (e.g., `agent`, `frontend`, `backend`, `testing`, `docs`, `week-1`).
- Mention the issue number in your commits and PRs, e.g. `#7`.

## 5. Making Commits

```bash
git status                 # see what changed
git add <file1> <file2>    # stage specific files
git commit -m "Add acceptance criteria to requirements schema"
```

**Good commit messages**
- Start with a verb in the imperative mood: *Add*, *Fix*, *Update*, *Remove*, *Refactor*.
- Keep the first line short (about 50–72 characters).
- Describe *what* and *why*, not just "changes" or "update".

| Good | Avoid |
|---|---|
| `Add localStorage persistence to CRUD template` | `stuff` |
| `Fix delete button not refreshing the list (#14)` | `fixed it` |
| `Update architecture schema with navigation field` | `final final v2` |

**Before committing, check:**
- No `.env` file, API keys, or passwords.
- No `node_modules/`, `venv/`, or other generated folders (`.gitignore` handles most of these).
- Only files related to your task.

## 6. Pushing Your Branch

```bash
# First push of a new branch
git push -u origin feature/<your-branch>

# Later pushes
git push
```

## 7. Opening a Pull Request

1. Go to the repository on GitHub — a banner will offer **Compare & pull request**.
2. Base: `main` ← Compare: `feature/<your-branch>`.
3. Fill in the [pull request template](../.github/PULL_REQUEST_TEMPLATE.md):
   - Summary of changes
   - Related issue (e.g., `Closes #12`)
   - Files changed
   - Testing performed
   - Integration dependencies
4. Request a review from at least one teammate — and from the owner of any shared file you touched.
5. Open the PR as a **Draft** if it is not ready yet, so others can see progress early.

Keep PRs small and focused; they are faster to review and easier to merge.

## 8. Reviewing a Pull Request

As a reviewer:
- Read the description and the changed files (*Files changed* tab).
- Check that the change matches the issue and stays within scope.
- Check that it follows the agreed JSON schemas and API contracts.
- Make sure no secrets or unnecessary files are included.
- Leave clear, kind, specific comments.
- Choose **Approve**, **Comment**, or **Request changes**.

As the author:
- Respond to every comment, push fixes to the same branch (the PR updates automatically), and re-request review.

## 9. Merging into `main`

- A PR can be merged after **at least one approval**, with all comments resolved and no merge conflicts.
- Use **Squash and merge** or **Merge pull request** as agreed by the team.
- After merging, delete the short-lived branch on GitHub if it is no longer needed.

## 10. Keeping Your Branch Synchronized

Do this at least once a day, and always before opening a PR:

```bash
git checkout main
git pull origin main
git checkout feature/<your-branch>
git merge main
```

### Resolving merge conflicts

If Git reports a conflict:
1. Open the conflicting files and look for `<<<<<<<`, `=======`, `>>>>>>>` markers.
2. Keep the correct content and remove the markers. If the conflict is in someone else's file, talk to her before deciding.
3. Then:

   ```bash
   git add <resolved-files>
   git commit
   git push
   ```

## 11. Quick Reference

| Task | Command |
|---|---|
| See current branch and changes | `git status` |
| Switch branch | `git checkout <branch>` |
| Create branch | `git checkout -b <branch>` |
| Get latest changes | `git pull` |
| Stage files | `git add <file>` |
| Commit | `git commit -m "message"` |
| Push | `git push` |
| View history | `git log --oneline` |
| Discard local changes to a file | `git restore <file>` |

When in doubt, ask in the team chat before running a command you are unsure about — especially anything with `--force`, `reset --hard`, or deleting branches.
