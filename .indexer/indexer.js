// Smart Indexer for ZenGlow
// Watches for new/changed files and folders, updates registry, and creates YAML sidecars

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

let chokidar = null;
try {
  chokidar = require('chokidar');
} catch (_) {
  // optional dependency; we'll fallback to one-shot update
}
const { getFileIcon } = require('./fileIcons');

const configPath = path.join(__dirname, 'indexer.config.yaml');
const registryPath = path.join(__dirname, 'registry.yaml');
const docsRoot = path.join(process.cwd(), 'Docs');
const docsReadme = path.join(docsRoot, 'README.md');

function listMarkdownFiles(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir)) {
    const p = path.join(dir, entry);
    const st = fs.statSync(p);
    if (st.isDirectory()) out.push(...listMarkdownFiles(p));
    else if (st.isFile() && entry.toLowerCase().endsWith('.md')) out.push(p);
  }
  return out;
}

function buildDocsQuickLinks() {
  if (!fs.existsSync(docsRoot)) return null;
  // Collect all markdowns
  const targets = listMarkdownFiles(docsRoot);

  if (targets.length === 0) return null;

  // Prefer to show a few top-level important docs first if present
  const priority = new Set([
    'project/PROJECT_OUTLINE.md',
    'backend/FLASK_BACKEND_ARCHITECTURE.md',
    'api/API_DOCUMENTATION.md',
  ]);
  const sorted = targets
    .map((p) => ({ p, rel: path.relative(docsRoot, p).replace(/\\/g, '/') }))
    .sort((a, b) => {
      const aPri = priority.has(a.rel) ? 0 : 1;
      const bPri = priority.has(b.rel) ? 0 : 1;
      if (aPri !== bPri) return aPri - bPri;
      return a.rel.localeCompare(b.rel);
    });

  const lines = ['# ZenGlow Documentation Index', ''];
  for (const { p, rel } of sorted) {
    try {
      const firstLine = fs.readFileSync(p, 'utf8').split(/\r?\n/)[0];
      const title = firstLine.startsWith('# ') ? firstLine.replace(/^#\s*/, '') : rel;
      lines.push(`- ${title}: [Docs/${rel}](${rel})`);
    } catch (_) {
      lines.push(`- ${rel}: [Docs/${rel}](${rel})`);
    }
  }
  lines.push('');

  return lines.join('\n');
}

function ensureDocsReadmeIndex() {
  const indexBlock = buildDocsQuickLinks();
  if (!indexBlock) return;
  let content = fs.existsSync(docsReadme) ? fs.readFileSync(docsReadme, 'utf8') : '';
  // Always rewrite everything before the Supabase CLI section
  const anchor = '# Supabase CLI';
  const pos = content.indexOf(anchor);
  if (pos >= 0) {
    const rest = content.slice(pos);
    content = `${indexBlock}\n${rest}`;
  } else {
    content = `${indexBlock}\n${content}`;
  }
  fs.writeFileSync(docsReadme, content);
}

function loadConfig() {
  return yaml.load(fs.readFileSync(configPath, 'utf8'));
}

function loadRegistry() {
  if (!fs.existsSync(registryPath))
    return {
      name: 'root',
      type: 'directory',
      children: {},
      icon: 'file-directory',
      iconFont: 'octicon',
    };
  return yaml.load(fs.readFileSync(registryPath, 'utf8'));
}

function saveRegistry(registry) {
  fs.writeFileSync(registryPath, yaml.dump(registry));
}

function createSidecar(filePath, info) {
  const sidecarPath = filePath + '.sidecar.yaml';
  fs.writeFileSync(sidecarPath, yaml.dump(info));
}

function getFileInfo(filePath) {
  const stats = fs.statSync(filePath);
  const iconInfo = getFileIcon(filePath);
  return {
    name: path.basename(filePath),
    type: 'file',
    size: stats.size,
    mtime: stats.mtime,
    ctime: stats.ctime,
    ext: path.extname(filePath),
    icon: iconInfo.icon,
    iconFont: iconInfo.font,
  };
}

function getOrCreateDirNode(root, dirParts) {
  let node = root;
  for (const part of dirParts) {
    if (!node.children) node.children = {};
    if (!node.children[part]) {
      node.children[part] = {
        name: part,
        type: 'directory',
        children: {},
        icon: 'file-directory',
        iconFont: 'octicon',
      };
    }
    node = node.children[part];
  }
  return node;
}

function updateRegistryForFile(registry, filePath) {
  const info = getFileInfo(filePath);
  const relPath = path.relative(process.cwd(), filePath);
  const parts = relPath.split(path.sep);
  const fileName = parts.pop();
  const dirNode = getOrCreateDirNode(registry, parts);
  if (!dirNode.children) dirNode.children = {};
  dirNode.children[fileName] = info;
  createSidecar(filePath, info);
}

function updateRegistryForDir(registry, dirPath) {
  const relPath = path.relative(process.cwd(), dirPath);
  const parts = relPath.split(path.sep);
  getOrCreateDirNode(registry, parts);
}

function removeFromRegistry(registry, filePath) {
  const relPath = path.relative(process.cwd(), filePath);
  const parts = relPath.split(path.sep);
  const fileName = parts.pop();
  let node = registry;
  for (const part of parts) {
    if (!node.children || !node.children[part]) return;
    node = node.children[part];
  }
  if (node.children && node.children[fileName]) {
    delete node.children[fileName];
  }
  try {
    fs.unlinkSync(filePath + '.sidecar.yaml');
  } catch {}
}

function removeDirFromRegistry(registry, dirPath) {
  const relPath = path.relative(process.cwd(), dirPath);
  const parts = relPath.split(path.sep);
  const dirName = parts.pop();
  let node = registry;
  for (const part of parts) {
    if (!node.children || !node.children[part]) return;
    node = node.children[part];
  }
  if (node.children && node.children[dirName]) {
    delete node.children[dirName];
  }
}

function main() {
  const config = loadConfig();
  let registry = loadRegistry();

  // Always try to ensure Docs index at startup
  ensureDocsReadmeIndex();

  if (!chokidar) {
    console.warn('chokidar not installed; ran one-shot Docs index update.');
    return;
  }

  const watcher = chokidar.watch(config.watch_paths, { ignoreInitial: false });

  watcher
    .on('add', (filePath) => {
      updateRegistryForFile(registry, filePath);
      saveRegistry(registry);
      console.log('Indexed file:', filePath);
      if (filePath.startsWith(docsRoot)) ensureDocsReadmeIndex();
    })
    .on('change', (filePath) => {
      updateRegistryForFile(registry, filePath);
      saveRegistry(registry);
      console.log('Updated file:', filePath);
      if (filePath.startsWith(docsRoot)) ensureDocsReadmeIndex();
    })
    .on('unlink', (filePath) => {
      removeFromRegistry(registry, filePath);
      saveRegistry(registry);
      console.log('Removed file:', filePath);
      if (filePath.startsWith(docsRoot)) ensureDocsReadmeIndex();
    })
    .on('addDir', (dirPath) => {
      updateRegistryForDir(registry, dirPath);
      saveRegistry(registry);
      console.log('Indexed directory:', dirPath);
      if (dirPath.startsWith(docsRoot)) ensureDocsReadmeIndex();
    })
    .on('unlinkDir', (dirPath) => {
      removeDirFromRegistry(registry, dirPath);
      saveRegistry(registry);
      console.log('Removed directory:', dirPath);
      if (dirPath.startsWith(docsRoot)) ensureDocsReadmeIndex();
    });
}

main();
