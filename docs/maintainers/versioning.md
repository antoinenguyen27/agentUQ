---
title: Docs Versioning Workflow
description: How the AgentUQ docs site handles Docusaurus versioning, current-version labeling, and future release snapshots.
slug: /maintainers/versioning
sidebar_position: 8
---

# Docs Versioning Workflow

The docs site is configured to present the current docs as version `0.1.0` without a one-item dropdown. That keeps the launch UX clean while still making the release visible.

## Current behavior

- Docs are served at `/`.
- The current docs label is `0.1.0`.
- There is no version dropdown yet because there is only one public docs version.

## When you cut the next docs release

From `website/`:

```bash
npm run docs:version <current-release>
```

For the first frozen snapshot of this site, that command would be:

```bash
npm run docs:version 0.1.0
```

That snapshots the current docs into Docusaurus versioned docs and writes the matching sidebars snapshot.

## After creating the first frozen version

1. Decide what label the live docs should show next.
2. Update `website/docusaurus.config.ts` so `versions.current.label` reflects that next live label.
3. Add a version dropdown to the navbar only once there is more than one meaningful public version to switch between.

## Vercel deployment shape

- Import the repo into Vercel.
- Set the project root directory to `website`.
- The build command can stay `npm run build`.
- Analytics are already wired in code; enable Web Analytics in the Vercel dashboard to activate them.
