## 2026-03-10 16:56:13

You are a senior staff software engineer responsible for initializing a repository designed for spec-driven AI development.
The repository should NOT assume any programming language, framework, or runtime yet.
Its purpose is to provide the structure and documentation needed to design and build a project later using AI-assisted development.
Create the following repository structure:
repo/
│
├ architecture.md
├ tasks.md
├ README.md
│
├ specs/
│   ├ api.md
│   ├ schema.md
│   └ requirements.md
│
├ prompts/
│   ├ implement_task.md
│   ├ code_review.md
│   ├ generate_tests.md
│   ├ architecture_review.md
│   └ refactor.md
│
├ decisions/
│   └ adr_template.md
│
├ docs/
│   └ notes.md
│
└ .gitignore
Populate each file with useful starter content.
architecture.md
Should contain:
- project overview placeholder
- goals
- architecture principles
- tech stack placeholder
- coding standards
- system design notes
tasks.md
Should explain how tasks will be generated once architecture.md is complete.
README.md
Should explain:
- spec-driven development workflow
- how architecture.md drives development
- how tasks.md is used
- how prompts are used with AI coding tools
specs/
These files should contain placeholder sections for future system specs such as:
- API contracts
- database schema
- system requirements
prompts/
Create reusable AI prompt templates for:
- implementing tasks
- performing code reviews
- generating tests
- reviewing architecture
- refactoring code
decisions/
Create an ADR (architecture decision record) template.
docs/
General notes and design discussions.
Constraints:
- Do not assume any programming language
- Keep files simple and readable
- Focus on enabling a spec-driven AI development workflow
Before creating files:
First generate a brief plan for the repository setup.
Then create the files.

