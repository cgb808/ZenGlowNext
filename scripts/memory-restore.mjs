#!/usr/bin/env node
/**
 * memory-restore.mjs
 *
 * Purpose: Restore a previously saved knowledge-graph snapshot (run-YYYY...) to
 *          the active working set (duplicating files OR updating `latest`).
 * Strategy: Copies snapshot contents back into root (excluding other run-* dirs)
 *           unless --latest-only is specified (just repoints the symlink / file).
 *
 * NOTE: This does not delete newer run-* directories; it only repopulates root.
 *       Use --clean-root to remove existing top-level files before restoring.
 *
 * Usage:
 *   node scripts/memory-restore.mjs --run run-20250819-220821
 *   node scripts/memory-restore.mjs --run run-20250819-220821 --clean-root
 *   node scripts/memory-restore.mjs --run run-20250819-220821 --latest-only
 */
import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, "..");

function parseArgs() {
  const args = process.argv.slice(2);
  const out = {
    run: null,
    graphRoot: null,
    latestOnly: false,
    cleanRoot: false,
    dryRun: false,
  };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--run") out.run = args[++i];
    else if (a === "--graph-root") out.graphRoot = args[++i];
    else if (a === "--latest-only") out.latestOnly = true;
    else if (a === "--clean-root") out.cleanRoot = true;
    else if (a === "--dry-run") out.dryRun = true;
  }
  if (!out.run) throw new Error("Missing --run <run-id>");
  return out;
}

async function pathExists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function resolveGraphRoot(explicit) {
  if (explicit) return explicit;
  const candidates = [
    process.env.KNOWLEDGE_GRAPH_ROOT,
    path.join(repoRoot, "..", "Artifact", "knowledge-graph"),
    path.join(repoRoot, "knowledge-graph"),
  ].filter(Boolean);
  for (const c of candidates) if (await pathExists(c)) return c;
  throw new Error(
    "No knowledge-graph root found. Provide --graph-root or set KNOWLEDGE_GRAPH_ROOT."
  );
}

async function restore(opts) {
  const root = await resolveGraphRoot(opts.graphRoot);
  const runDir = path.join(root, opts.run);
  const latestLink = path.join(root, "latest");
  if (!(await pathExists(runDir)))
    throw new Error(`Run directory not found: ${runDir}`);
  console.log("[info] graph-root:", root);
  console.log("[info] restoring run:", opts.run);

  if (opts.latestOnly) {
    if (opts.dryRun) {
      console.log("[dry-run] would repoint latest ->", opts.run);
    } else {
      try {
        await fs.rm(latestLink, { recursive: true, force: true });
      } catch {}
      try {
        await fs.symlink(opts.run, latestLink, "dir");
      } catch {
        await fs.writeFile(latestLink, opts.run + "\n");
      }
      console.log("[done] latest repointed");
    }
    return;
  }

  // Collect candidate root-level files to remove (only those known types)
  const safeNames = new Set([
    "entities.json",
    "relations.json",
    "memory_graph.mmd",
    "COMPREHENSIVE_SYSTEM_CAPTURE.md",
    "graph.json",
    "manifest.json",
  ]);
  // Add memory_snapshot_* present in run
  for (const f of await fs.readdir(runDir))
    if (/^memory_snapshot_/.test(f)) safeNames.add(f);

  if (opts.cleanRoot) {
    for (const name of safeNames) {
      const target = path.join(root, name);
      if (await pathExists(target)) {
        if (opts.dryRun) console.log("[dry-run] remove", name);
        else await fs.rm(target, { force: true });
      }
    }
  }

  // Copy files from runDir back to root
  for (const name of safeNames) {
    const src = path.join(runDir, name);
    if (!(await pathExists(src))) continue;
    const dest = path.join(root, name);
    if (opts.dryRun) console.log("[dry-run] copy", src, "->", dest);
    else await fs.copyFile(src, dest);
  }

  // Update latest pointer as a courtesy
  if (!opts.dryRun) {
    try {
      await fs.rm(latestLink, { recursive: true, force: true });
    } catch {}
    try {
      await fs.symlink(opts.run, latestLink, "dir");
    } catch {
      await fs.writeFile(latestLink, opts.run + "\n");
    }
  }

  console.log(
    opts.dryRun ? "[dry-run] restore simulated" : "[done] restore complete"
  );
}

restore(parseArgs()).catch((e) => {
  console.error("[fatal]", e.message);
  process.exit(1);
});
