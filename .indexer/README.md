# ZenGlow Smart Indexer

This indexer watches for new or changed files and folders in the configured paths, updates a central YAML registry, and creates YAML sidecar files for each indexed file.

## How it works

- Watches paths defined in `.indexer/indexer.config.yaml`.
- On file/folder add/change/remove, updates `.indexer/registry.yaml`.
- For each file, creates a `[filename].sidecar.yaml` with metadata.

## Usage

1. **Install dependencies:**
   ```sh
   npm install js-yaml chokidar
   ```
2. **Run the indexer:**
   ```sh
   node .indexer/indexer.js
   ```

## Configuration

- Edit `.indexer/indexer.config.yaml` to set watch paths, sidecar extension, and registry location.

## Output

- `.indexer/registry.yaml`: Central registry of indexed files and directories.
- `[filename].sidecar.yaml`: Metadata sidecar for each file.

---

**Note:**

- The indexer must be running to detect changes in real time.
- You can extend the script to add more metadata or custom logic as needed.
