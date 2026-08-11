# auto-scaffold: automatic scaffolding for new projects

## Trigger condition (all three must hold)
1. The user is describing "wanting to build something new" -- a new
   product/tool/website/system -- not: asking a question, chatting,
   modifying existing code, or adding a feature to an existing project;
2. The current directory is not inside any git repo (`git rev-parse
   --git-dir` fails), and the current directory has no `docs/` or
   `.claude/` (i.e. it isn't an already-scaffolded project);
   Exception: when the current directory is the user's home directory
   `$HOME` itself, `~/.claude` is Claude's own config directory, not a
   project marker -- `$HOME` not being a git repo is still treated as
   satisfying this condition;
3. This conversation hasn't already created a project for this request.

When unsure whether something counts as a new project: don't trigger, keep
working as usual -- better to miss a scaffold than to create a garbage
folder by mistake.
When the user explicitly says "no need to create a project / just edit it
here": don't trigger.
An existing repo that's missing docs is not this rule's concern -- don't
proactively backfill scaffolding for it.

## Action once triggered (execute silently, never pause to ask, never present options)
1. Distill an English kebab-case project name from the request sentence
   (e.g. "a small expense-tracking tool" -> `expense-tracker`);
2. Determine the projects root: if the file
   `~/.claude/workflow-projects-root` exists, use its content as the root,
   otherwise default to `~/Projects`; create `<root>/<project-name>/` and
   `cd` into it;
   - If `<root>/<project-name>/` already exists: don't reuse it, don't
     overwrite it -- treat this as "unsure" -- skip auto-creation this
     time, give a one-line note, and keep working in place;
   - If creation or writing fails (including the user declining
     authorization): don't retry; remove any empty directory just
     created, leaving no leftover; give a one-line note "couldn't
     auto-create the project, working in place instead" and continue
     normally;
3. Lay down scaffolding per the scaffold skill's "Auto mode" (tech stack
   follows the fixed baseline, no questions asked; fill in whatever can be
   filled from the user's request sentence, leave the rest as template
   placeholders; includes `git init` + the initial commit);
4. Report in one line: "Created project <name> at <path>, this request
   will live there from now on" -- then immediately continue with what the
   user actually asked for, without stopping to wait for confirmation.

## Disabling
`touch ~/.claude/.auto-scaffold-off` disables this globally (the hook
checks for the file and stops injecting once it exists).
