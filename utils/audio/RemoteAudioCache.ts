import * as FileSystem from 'expo-file-system';

const CACHE_DIR = FileSystem.cacheDirectory + 'audio/';

async function ensureCacheDir() {
  try {
    const info = await FileSystem.getInfoAsync(CACHE_DIR);
    if (!info.exists) {
      await FileSystem.makeDirectoryAsync(CACHE_DIR, { intermediates: true });
    }
  } catch (e) {
    // noop
  }
}

function safeName(input: string) {
  // Create a safe filename from URL; keep it deterministic and short
  return input
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 80);
}

export async function getCachedUri(url: string, ttlMs: number = 1000 * 60 * 60 * 24) {
  await ensureCacheDir();
  const name = safeName(url);
  const path = `${CACHE_DIR}${name}.bin`;
  try {
    const info = await FileSystem.getInfoAsync(path);
    const now = Date.now();
    if (info.exists && info.modificationTime) {
      const ageMs = now - info.modificationTime * 1000;
      if (ageMs < ttlMs) {
        return path;
      }
    }
  } catch {}

  // Download fresh copy
  try {
    await FileSystem.downloadAsync(url, path);
    return path;
  } catch (e) {
    // If download fails but previous file exists, fall back to it
    const info = await FileSystem.getInfoAsync(path);
    if (info.exists) return path;
    throw e;
  }
}

export async function prefetch(urls: string[], ttlMs?: number) {
  const out: Record<string, string> = {};
  await Promise.all(
    urls.map(async (u) => {
      try {
        out[u] = await getCachedUri(u, ttlMs);
      } catch {}
    }),
  );
  return out;
}
