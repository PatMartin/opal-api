Write a thorough README.md for this project. The README is the front door
of the repository: a new contributor should be able to understand what the
project is, why it exists, how it is structured, and how to build, run,
test, and extend it without reading the source first.

Before writing anything, explore the repository and ground every claim in
what actually exists. Do not invent features, commands, or structure.

DISCOVERY

1. Read the manifest(s) for the ecosystem: package.json, pyproject.toml,
   setup.py, requirements.txt, Cargo.toml, go.mod, pom.xml, build.gradle,
   Dockerfile, docker-compose.yml — whichever exist. Record the project
   name, version, description, license, scripts, and dependencies.
2. Map the directory tree. Identify entry points, source roots, test
   roots, configuration files, CI/CD definitions (.github/workflows or
   equivalent), documentation directories, and generated/vendored paths
   that should be excluded from the description.
3. Read the main entry points and a representative sample of modules.
   Understand the architecture: what the components are, how they interact,
   and what external systems (APIs, databases, message buses, hardware)
   the project touches.
4. Read the test setup and CI workflows. Record the exact commands used
   to build, lint, test, and validate — use the same commands in the
   README, never paraphrased versions that might not run.
5. Check git history and existing docs (docs/, CONTRIBUTING.md,
   CHANGELOG.md, AGENTS.md) for conventions, terminology, and prior
   explanations worth reusing.

REQUIRED SECTIONS

Include every section that applies to the project; omit only what
genuinely does not exist, and never leave placeholder TODOs.

- Title and one-line description.
- Badges for CI status, license, and package version when the project
  publishes them (link to the real workflow/package, not a generic URL).
- Overview: 1-3 paragraphs explaining what the project does, the problem
  it solves, and who it is for. State the maturity/status honestly.
- Highlights or Features: a tight bulleted list of capabilities, grounded
  in real code, not marketing language.
- Architecture or Project Structure: a diagram or annotated tree of the
  major components and how data/control flows between them. For API or
  multi-service projects, include a table of the services/modules and
  their responsibilities.
- Requirements: runtimes, tools, and minimum versions, with version
  numbers verified against manifests and CI configuration.
- Installation: exact, ordered, copy-pasteable commands.
- Quickstart / Usage: the smallest end-to-end example that proves the
  project works, plus coverage of the main workflows. Show real CLI
  commands, code snippets, or API calls taken from the codebase — with
  expected output where helpful.
- Configuration: environment variables, config files, and settings with
  defaults and semantics.
- Development: how to set up a dev environment, run the linter,
  formatter, type checker, and test suite; how the project is organized
  for contributors; naming/style conventions worth knowing.
- Testing/Validation: the exact commands and what each stage checks.
- Documentation pointers: links to deeper docs inside and outside the
  repo, with a one-line description of each.
- Contributing: contribution workflow, branch/commit conventions, and
  how to run CI checks locally before pushing.
- License, and author/maintainer contact when recorded in the manifest.
- Table of contents with anchor links for any README long enough to
  need one.

WRITING STANDARDS

- Be precise and factual. Every command, path, flag, version, and file
  name must exist in the repo. Never describe aspirational or planned
  features as existing.
- Prefer short sections and scannable formatting: tables for structured
  comparisons, fenced code blocks with language tags for commands and
  output, collapsible sections only where they help.
- Write for the reader's first visit: define project-specific terms and
  acronyms on first use.
- Use relative links for files and directories inside the repository so
  they work on any branch or fork.
- Match the tone and conventions of existing project docs when present.
- Do not duplicate information that belongs in linked docs; summarize
  and link instead. Keep the README authoritative but not exhaustive.

VERIFICATION

Before finishing: re-check every command and path you wrote against the
repo, run the build/test commands you documented where feasible, confirm
every internal link resolves, and proofread the rendered Markdown for
broken tables, unclosed code fences, and heading hierarchy.
