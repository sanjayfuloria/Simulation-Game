# SAAS Demo — Community Contribution

This folder contains a small Next.js demo that demonstrates streaming OpenAI responses rendered progressively as Markdown.

Contents:
- `docs/saas_demo_notebook.ipynb` — Notebook with examples for calling the local and deployed APIs.
- `README.md` — This file.

How to run locally
1. Set your OpenAI key in the shell:

```bash
export OPENAI_API_KEY="sk-..."
```

2. Install dependencies and run:

```bash
npm install
npm run dev
```

3. Open http://localhost:3000 and try the demo.

Notes
- The live demo uses Vercel; set `OPENAI_API_KEY` in the Vercel project settings to enable streaming in production.
- This folder intentionally contains only documentation and the notebook; the full app is at the repository root.