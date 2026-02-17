# OpenCode Skills

This directory contains custom skills for the OpenCode AI assistant.

## Available Skills

### git_commit_workflow

**Purpose:** Analyze changes, create logical commits with conventional messages, and push to remote.

**Usage:**
When you want to commit changes, I will:
1. Verify this is a git repository
2. Check for remote configuration
3. Analyze and categorize your changes
4. Present a commit plan with conventional commit messages
5. Execute commits after your approval
6. Push to remote (with your permission)
7. Show final status

**Conventional Commit Types:**
- `feat:` - New features
- `fix:` - Bug fixes
- `refactor:` - Code restructuring
- `docs:` - Documentation changes
- `style:` - CSS, formatting
- `test:` - Test files
- `chore:` - Maintenance, dependencies
- `config:` - Configuration files

**Example:**
```
User: "Commit my changes"
→ Analyzes git status
→ Groups files logically
→ Proposes: "feat: add user authentication"
→ Commits after approval
→ Offers to push
```

---

## Adding New Skills

To add a new skill:
1. Create a new `.md` file in this directory
2. Follow the skill documentation format
3. Include clear steps and rules
4. Test the skill workflow

## Skill Format

Skills should include:
- **Purpose**: What the skill does
- **Steps**: Numbered workflow steps
- **Commands**: Specific bash commands to run
- **Rules**: Guidelines and constraints
- **Examples**: Usage examples
