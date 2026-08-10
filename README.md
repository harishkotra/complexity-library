# Complexity Library

An open-source, deterministic-first library for understanding how code scales. Submit a function, inspect the syntax facts behind the result, and operate a reproducible visualization of its growth.

## Why it exists

Complexity Library is an algorithm visualizer, code knowledge library, and interactive Big-O learning tool—not a chatbot. It analyzes functions as artifacts and treats AI as an optional, constrained fallback for ambiguity rather than the product surface.

## Current capabilities

- Deterministic Python, JavaScript, and TypeScript parsing for constant, linear, logarithmic, n-log-n, quadratic, cubic, and branching-recursion patterns.
- Structured time/space complexity, confidence, assumptions, limitations, AST fingerprints, and visualization specs.
- Browser-native visual workbench with real server-sent analysis stages.
- Public library/detail routes with a small curated catalog and functional search/filter controls.
- Anonymous session cookies, exact normalized-code reuse, and a Supabase-ready repository/migration path.
- No submitted code execution and no LLM dependency for supported deterministic analyses.

## Project structure

```text
apps/api       FastAPI analysis API
apps/web       Next.js visual workbench
packages/      Versioned shared schemas/types
supabase/      PostgreSQL/pgvector migrations and seed assets
```

## Local development

### API

```bash
cd apps/api
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

### Web

```bash
pnpm install
pnpm dev:web
```

The web app starts at `http://localhost:3000`; its deterministic analysis API is `http://localhost:8000`. Copy `.env.example` to the relevant app environment file to override defaults.

## Tests and build

```bash
cd apps/api && uv run pytest
cd ../web && ./node_modules/.bin/next build
```

## Configuration

The application works without an LLM configuration for supported deterministic Python functions. Set Supabase variables to use durable server-side persistence; never expose a service-role key to the browser.

### Supported analysis subset

Python uses the standard AST. JavaScript and TypeScript use tree-sitter and currently support top-level function declarations, loops, nested loops, conventional binary search, direct recursion, array allocation, and built-in sorting recognition. Unsupported constructs reduce confidence only when they are encountered; the app does not claim support for languages it cannot parse.

## Contributing

Issues and pull requests are welcome. Keep user code and prompts untrusted, preserve the deterministic-first architecture, and add focused regression tests for every analysis rule or visualization contract change.

## Current slice

The initial slice supports deterministic Python analysis of straightforward constant, linear, logarithmic, n-log-n, quadratic, cubic, and recursive functions. It deliberately does not execute submitted code or call an LLM.

## License

[MIT](LICENSE)
