# Getting started with IncTec Forge

## 1. Install it into your repo (2 minutes)

From the root of your project repo, pick the agent(s) you use:

```bash
# one command, no clone needed (uses your GitHub login — the forge repo is private)
bash <(gh api repos/abdulra7ma/inctec-forge/contents/bootstrap.sh -H "Accept: application/vnd.github.raw") --agent claude

# or, if you already have the forge cloned somewhere
python3 ~/code/inctec-forge/install.py --agent claude
```

Agents: `claude`, `codex`, `gemini`, `cursor`, `copilot`, `opencode`, `aider` — combine them with commas
(`--agent claude,cursor`). Leave `--agent` out and the installer asks you.

What happens:
- The core system lands in your repo: `AGENTS.md`, `.agents/` (roles, skills, config, risk rules), `docs/engineering/`,
  `scripts/`, `factory/`, CI, and the local dev/observability stack.
- Only the adapters your agent needs are generated (Claude gets `CLAUDE.md`, sub-agents and hooks; Gemini gets a settings
  file; Codex, Cursor, Copilot and opencode read `AGENTS.md` and `.agents/skills/` natively, so they need nothing extra).
- Your existing files are never overwritten — if you already have a `Makefile`, the forge version is saved as
  `Makefile.forge-new` for you to merge.
- Git hooks are switched on and everything is committed on a new branch `chore/forge-setup`.

Then: `git push -u origin chore/forge-setup`, open a PR, merge it.

**Later updates:** `python3 install.py --update` (or the bootstrap command with `--update`) refreshes roles, skills,
scripts and docs from the latest forge. Your `.agents/config.toml` and `.agents/risk-rules.json` are never overwritten.

## 2. Your first day

1. Read `AGENTS.md` (5 minutes). It's what every agent reads first, so you should know what it says.
2. Skim `docs/engineering/autonomy.md` — the T0–T3 tiers decide what an agent may do alone.
3. Open your agent in the repo and give it a small, real ticket.

### In Claude Code
```
/build-feature add a ?status= filter to GET /devices
```
Other slash commands: `/grill` (stress-test an idea before building), `/design-doc`, `/review`, `/ship`, `/debug`, `/factory`.
Specialist sub-agents (`code-reviewer`, `security-reviewer`, `architect`, …) are picked up automatically.

### In Codex, Cursor, Copilot, Gemini CLI, opencode
These read `AGENTS.md` automatically and find skills in `.agents/skills/` by their descriptions. Just ask naturally,
or name the skill: *"Use the build-feature skill to add a ?status= filter to GET /devices."*

### In Aider
`.aider.conf.yml` loads `AGENTS.md`. Add the skill you need to the chat: `/read .agents/skills/build-feature/SKILL.md`.

## 3. What a normal feature looks like

```
you: "add a status filter to /devices"
 → agent restates the goal, finds related code, predicts tier (T1)
 → (T2+ or vague? it grills you with 3–5 sharp questions first)
 → plan → tests first → code → make check
 → fresh-context review (code + security; UX/UI if frontend changed)
 → /ship: commits on feat/… and opens a PR labelled tier:T1
 → you review and merge
```
Anything touching migrations, auth, API contracts, CI or infra becomes T2: the agent writes a design note in
`docs/design/` and opens a **draft** PR for a code owner. T3 (prod, secrets, destructive data) is never committed by an agent.

## 4. Unattended: the factory

```bash
make factory f="Add a ?status= filter to GET /devices"
make factory-status
```
Spec → build → parallel reviews (max 2 fix rounds) → approver. Only T0 auto-merges; everything else ends as a PR for
a human. Try it offline first: `python3 factory/run.py new "smoke test" --runtime stub`.
Pick which tool/model plays each role in `.agents/config.toml` → `[roles]` (e.g. build with Claude, review with Codex).

## 5. When things push back

| You see | It means | Do |
|---|---|---|
| `✋ Direct commits to 'main' are not allowed` | git hook | `git switch -c feat/<slug>` |
| `✋ Agent commit blocked: staged change is tier T3` | an agent tried to commit something destructive | read the change; a human commits it after review |
| CI `risk-tier` fails asking for a design note | PR is T2/T3 | add `docs/design/…` and link it in the PR body |
| CI `agents-sync` fails | someone edited `.agents/` without syncing | `make agents-sync`, commit |
| The classifier got the tier wrong | rules don't fit your repo yet | tune `.agents/risk-rules.json` (that change is itself T2) |
