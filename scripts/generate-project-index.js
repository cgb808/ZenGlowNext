#!/usr/bin/env node

/**
 * This script generates a structured JSON index of the project's file system.
 * It respects .gitignore patterns to exclude irrelevant files and directories,
 * creating a clean map of the codebase suitable for AI agent context.
 */

import fs from 'fs/promises';
import { createReadStream } from 'fs';
import path from 'path';
import crypto from 'crypto';
import ignore from 'ignore';

const projectRoot = process.cwd();
const outputFile = path.join(projectRoot, 'project-index.json');
const markdownFile = path.join(projectRoot, 'project-index.md');

// A minimal list of patterns that should always be ignored for indexing,
// regardless of the .gitignore file.
const baseIgnorePatterns = [
  '.git',
  'node_modules',
  path.basename(outputFile), // Don't index the output file itself
  path.basename(markdownFile), // Don't index the markdown file either
];

/**
 * Reads and parses the .gitignore file from the project root.
 * @returns {Promise<string>} The content of the .gitignore file.
 */
async function readGitignore() {
  try {
    const gitignorePath = path.join(projectRoot, '.gitignore');
    return await fs.readFile(gitignorePath, 'utf-8');
  } catch (error) {
    if (error.code !== 'ENOENT') {
      console.error('❌ Error reading .gitignore:', error);
    }
    return ''; // Return empty string if .gitignore doesn't exist or fails to read
  }
}

/**
 * Calculates the SHA-256 hash of a file using streams to handle large files
 * efficiently without loading the entire file into memory.
 * @param {string} filePath - The path to the file.
 * @returns {Promise<string>} The SHA-256 hash of the file.
 */
function getFileHash(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = createReadStream(filePath);
    stream.on('error', (err) => reject(err));
    stream.on('data', (chunk) => hash.update(chunk));
    stream.on('end', () => resolve(hash.digest('hex')));
  });
}

async function createIndex(dir, ig) {
  let entries;
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch (error) {
    // This can happen with permission errors on directories we couldn't filter out before reading
    if (error.code === 'EACCES') {
      return null;
    }
    throw error;
  }

  const index = {};

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    const relativePath = path.relative(projectRoot, fullPath);

    // The ignore library works with relative paths
    if (ig.ignores(relativePath)) continue;

    if (entry.isDirectory()) {
      const subIndex = await createIndex(fullPath, ig);
      // Only include non-empty directories in the index
      if (subIndex && Object.keys(subIndex).length > 0) {
        index[entry.name] = subIndex;
      }
    } else {
      const stats = await fs.stat(fullPath); // follows symlinks

      // If this turned out to be a directory (e.g., a symlink to a directory), recurse instead of treating as file
      if (stats.isDirectory()) {
        const subIndex = await createIndex(fullPath, ig);
        if (subIndex && Object.keys(subIndex).length > 0) {
          index[entry.name] = subIndex;
        }
        continue;
      }
      // Pre-calculate hash for empty files and use streams for non-empty ones
      // to avoid memory issues with very large files.
      const hash =
        stats.size === 0
          ? 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' // SHA-256 for empty file
          : await getFileHash(fullPath);
      index[entry.name] = {
        type: 'file',
        size: stats.size,
        lastModified: stats.mtime.toISOString(),
        contentHash: hash,
      };
    }
  }
  return index;
}

/**
 * Converts the project index to a markdown representation.
 * @param {Object} index - The project index object.
 * @param {string} title - The title for the markdown document.
 * @returns {string} The markdown representation of the project index.
 */
function indexToMarkdown(index, title = 'Project Index') {
  const lines = [`# ${title}`, '', 'Generated project file structure and metadata.', ''];
  
  function processEntry(entry, name, level = 0) {
    const indent = '  '.repeat(level);
    
    if (entry.type === 'file') {
      const sizeFormatted = formatFileSize(entry.size);
      const lastModified = new Date(entry.lastModified).toLocaleDateString();
      lines.push(`${indent}- **${name}** (${sizeFormatted}, modified: ${lastModified})`);
    } else if (typeof entry === 'object') {
      // Directory
      lines.push(`${indent}- **${name}/**`);
      
      // Sort entries: directories first, then files
      const entries = Object.entries(entry);
      const dirs = entries.filter(([, value]) => typeof value === 'object' && !value.type);
      const files = entries.filter(([, value]) => value.type === 'file');
      
      [...dirs, ...files].forEach(([subName, subEntry]) => {
        processEntry(subEntry, subName, level + 1);
      });
    }
  }
  
  // Process root level entries
  const entries = Object.entries(index);
  const dirs = entries.filter(([, value]) => typeof value === 'object' && !value.type);
  const files = entries.filter(([, value]) => value.type === 'file');
  
  [...dirs, ...files].forEach(([name, entry]) => {
    processEntry(entry, name);
  });
  
  lines.push('', `---`, `Generated by: npm run generate-project-index`);
  
  return lines.join('\n');
}

/**
 * Formats file size in human-readable format.
 * @param {number} bytes - File size in bytes.
 * @returns {string} Formatted size string.
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

async function main() {
  console.log('🚀 Starting project indexing...');
  const gitignoreContent = await readGitignore();

  // Create an ignore instance and add all patterns
  const ig = ignore().add(gitignoreContent);
  ig.add(baseIgnorePatterns);

  const projectIndex = await createIndex(projectRoot, ig);
  
  // Write JSON file
  await fs.writeFile(outputFile, JSON.stringify(projectIndex, null, 2));
  console.log(`✅ Project index JSON created successfully at ${outputFile}`);
  
  // Write Markdown file
  const markdownContent = indexToMarkdown(projectIndex);
  await fs.writeFile(markdownFile, markdownContent);
  console.log(`✅ Project index Markdown created successfully at ${markdownFile}`);
}

main().catch((error) => console.error('❌ Error creating project index:', error));