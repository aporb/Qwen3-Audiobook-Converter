# Git Commit & Push Workflow

Analyze changes, create logical commits with conventional messages, and push to remote.

---

## Step 1: Verify Git Repository

**Check if current directory is a git repository:**

```bash
git rev-parse --git-dir
```

**If not a git repo:**
- Ask: "Not a git repository. Initialize it?"
- If yes: `git init`, ask about initial commit
- If no: Exit

---

## Step 2: Check Remote Repository

**Check if remote is configured:**

```bash
git remote -v
```

**If no remote:**
- Ask: "No remote configured. Set one up?"
- If yes: Get URL, run `git remote add origin <url>`
- If no: Note commits will be local only

---

## Step 3: Analyze Changes

**View actual changes:**

```bash
git status
git diff --cached
git diff
```

**Categorize changes into logical groups:**
- **Features** (new functionality)
- **Fixes** (bug corrections)
- **Refactor** (code restructuring)
- **Docs** (documentation)
- **Config** (configuration files)
- **Style** (CSS, formatting)
- **Tests** (test files)
- **Chore** (maintenance, dependencies)

---

## Step 4: Present Commit Plan

**Show grouped changes with proposed commits using conventional commits format:**

```example:
Group 1: Feature - User Authentication
- src/auth/login.ts (new)
- src/auth/register.ts (new)
Proposed: feat: implement user authentication system

Group 2: Fix - Navigation Bug
- src/components/Navbar.tsx (modified)
Proposed: fix: resolve mobile navigation menu not closing

Group 3: Docs - API Documentation
- docs/api/endpoints.md (modified)
Proposed: docs: update API documentation with auth endpoints
```

**Ask user:** "Does this commit plan look good? (Yes/No/Edit)"

---

## Step 5: Execute Commits

**For each approved group:**
1. Stage files: `git add <files>`
2. Commit: `git commit -m "<message>"`
3. Show progress: `✓ Committed: <message>`

**Verify:**
```bash
git log --oneline -5
```

---

## Step 6: Push to Remote

**If remote exists:**
- Ask: "Push commits to remote?"
- If yes:
  ```bash
  git branch --show-current
  git push -u origin <branch>  # or just git push
  ```
- Handle errors (conflicts, auth, missing branch)

**If no remote:**
- Inform commits are local only
- Ask: "Set up remote now?"
- If yes: Get URL, add remote, offer to push

---

## Step 7: Final Status

```bash
git status
```

**Show summary:**
```
✓ Workflow complete!
- Created X commits
- Pushed to remote: Yes/No
- Working directory clean
```

---

## Rules

- **No attribution** in commit messages (no "by [author]")
- Use **conventional commits**: feat:, fix:, refactor:, docs:, style:, test:, chore:
- Keep messages **concise but descriptive**
- **Group related changes** together
- **Ask before** irreversible actions
- Handle errors **gracefully** with helpful guidance
