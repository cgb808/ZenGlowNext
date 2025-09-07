#!/usr/bin/env node
/**
 * memory-save.mjs
 *
 * Purpose: Create a timestamped immutable snapshot (run-YYYYMMDD-HHMMSS) of the
 *          current knowledge-graph artifact set and update the `latest` pointer.
 *
 * Sources searched (first existing wins unless --graph-root provided):
 *   1. $KNOWLEDGE_GRAPH_ROOT
 *   2. ../Artifact/knowledge-graph
 *   3. ./knowledge-graph (inside repo)
 *
 * Files copied (if present):
 *   - entities.json
 *   - relations.json
 *   - memory_snapshot_*.json
 *   - COMPREHENSIVE_SYSTEM_CAPTURE.md
 *   - memory_graph.mmd
 *   - graph.json / manifest.json (prior run formats)
 *   - any additional *.md flagged with --include-md-glob
 *
 * Outputs:
 *   knowledge-graph/run-<timestamp>/... + manifest.json
 *   knowledge-graph/latest  (symlink or pointer file) updated atomically.
 *
 * Usage examples:
 *   node scripts/memory-save.mjs
 *   node scripts/memory-save.mjs --dry-run
 *   node scripts/memory-save.mjs --graph-root ../Artifact/knowledge-graph --note "post-ingest"
 */

import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import crypto from "crypto";
import { execSync } from "child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, "..");

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { dryRun: false, graphRoot: null, note: "", includeMdGlob: "" };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--dry-run") out.dryRun = true;
    else if (a === "--graph-root") out.graphRoot = args[++i];
    else if (a === "--note") out.note = args[++i];
    else if (a === "--include-md-glob") out.includeMdGlob = args[++i];
  }
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
  for (const c of candidates) {
    if (await pathExists(c)) return c;
  }
  throw new Error(
    "No knowledge-graph root found. Provide --graph-root or set KNOWLEDGE_GRAPH_ROOT."
  );
}

function timestamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

async function collectFiles(root, includeMdGlob) {
  const out = [];
  const addIf = async (rel) => {
    const p = path.join(root, rel);
    if (await pathExists(p)) out.push(rel);
  };
  await addIf("entities.json");
  await addIf("relations.json");
  await addIf("memory_graph.mmd");
  await addIf("COMPREHENSIVE_SYSTEM_CAPTURE.md");
  await addIf("graph.json");
  await addIf("manifest.json");
  // memory_snapshot_* files
  try {
    const items = await fs.readdir(root);
    for (const f of items) {
      if (/^memory_snapshot_\d{8}.*\.json$/.test(f)) out.push(f);
      if (includeMdGlob && f.endsWith(".md") && f.match(includeMdGlob))
        out.push(f);
    }
  } catch {}
  // Deduplicate
  return [...new Set(out)];
}

async function hashFile(p) {
  const buf = await fs.readFile(p);
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function gitRev() {
  try {
    return execSync("git rev-parse HEAD", {
      cwd: repoRoot,
      stdio: ["ignore", "pipe", "ignore"],
    })
      .toString()
      .trim();
  } catch {
    return null;
  }
}

async function main() {
  const opts = parseArgs();
  const root = await resolveGraphRoot(opts.graphRoot);
  const runId = `run-${timestamp()}`;
  const dest = path.join(root, runId);
  const latestLink = path.join(root, "latest");

  const files = await collectFiles(root, opts.includeMdGlob);
  if (!files.length) {
    console.error("[warn] No source files found to snapshot.");
  }
  console.log(`[info] graph-root: ${root}`);
  console.log(`[info] creating snapshot: ${runId}`);
  console.log(`[info] files: ${files.join(", ") || "(none)"}`);

  if (opts.dryRun) {
    console.log("[dry-run] exiting before file copy.");
    return;
  }

  await fs.mkdir(dest, { recursive: true });

  const manifest = {
    runId,
    createdAt: new Date().toISOString(),
    sourceRoot: root,
    gitCommit: gitRev(),
    note: opts.note || null,
    files: [],
    schemaVersion: 1,
  };

  for (const rel of files) {
    const src = path.join(root, rel);
    const target = path.join(dest, rel);
    try {
      const stat = await fs.stat(src);
      if (stat.isFile()) {
        await fs.copyFile(src, target);
        manifest.files.push({
          name: rel,
          sha256: await hashFile(src),
          bytes: stat.size,
        });
      }
    } catch (e) {
      console.warn("[warn] copy failed for", rel, e.message);
    }
  }

  // Write manifest
  await fs.writeFile(
    path.join(dest, "manifest.json"),
    JSON.stringify(manifest, null, 2)
  );

  // Update latest pointer (prefer symlink; fallback to pointer file)
  try {
    await fs.rm(latestLink, { recursive: true, force: true });
    await fs.symlink(runId, latestLink, "dir");
  } catch {
    await fs.writeFile(latestLink, runId + "\n");
  }

  console.log("[done] snapshot created at", dest);
}

main().catch((e) => {
  console.error("[fatal]", e.message);
  process.exit(1);
});
