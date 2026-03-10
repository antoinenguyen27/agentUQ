---
title: Docs Release Process
description: Step-by-step process for versioning the Docusaurus docs site and updating the live docs label.
slug: /maintainers/versioning
sidebar_position: 8
---

# Docs Release Process

This process is used when maintainers need to freeze a docs snapshot and advance the live docs label.

## Current configuration

- Docs are served at `/`.
- The live docs label is `0.1.0`.
- A version dropdown is not shown until there is more than one public docs version.

## When to run this process

- a public docs release needs to remain browsable after later changes
- the live docs label needs to move to the next release line

Do not cut a version for routine edits that belong to the current live release.

## Procedure

From `website/`, run:

```bash
npm run docs:version <current-release>
```

For the first frozen snapshot of this site, run:

```bash
npm run docs:version 0.1.0
```

Then complete the remaining release steps:

1. Decide what label the live docs should show next.
2. Update `website/docusaurus.config.ts` so `versions.current.label` reflects that next live label.
3. Review the generated versioned docs and sidebar snapshot.
4. Add a version dropdown to the navbar only after there is more than one public version worth exposing.
5. Build the site before deployment.

## Build and deployment

For local verification, run:

```bash
npm run build
```

Vercel settings:

- project root directory: `website`
- build command: `npm run build`
- enable Web Analytics in the Vercel dashboard if analytics should be active for the site
