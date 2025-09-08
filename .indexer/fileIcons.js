// File icon mapping using Octicons (default), with fallbacks for FontAwesome, Devicons, etc.
// Extend as needed for your file types and icon sets.

const path = require("path");

// Octicons: https://primer.style/octicons/
// FontAwesome: https://fontawesome.com/icons
// Devicons: https://devicon.dev/

const iconMap = {
  // Octicons
  ".js": { icon: "mark-github", font: "octicon" },
  ".ts": { icon: "code", font: "octicon" },
  ".tsx": { icon: "code-square", font: "octicon" },
  ".json": { icon: "file-code", font: "octicon" },
  ".md": { icon: "book", font: "octicon" },
  ".yaml": { icon: "file", font: "octicon" },
  ".yml": { icon: "file", font: "octicon" },
  ".mp3": { icon: "file-media", font: "octicon" },
  ".png": { icon: "file-media", font: "octicon" },
  ".jpg": { icon: "file-media", font: "octicon" },
  ".svg": { icon: "file-media", font: "octicon" },
  ".css": { icon: "paintbrush", font: "octicon" },
  ".html": { icon: "globe", font: "octicon" },
  ".exe": { icon: "terminal", font: "octicon" },
  ".sh": { icon: "terminal", font: "octicon" },
  ".py": { icon: "code", font: "octicon" },
  // Add more as needed
  // Fallback
  default: { icon: "file", font: "octicon" },
};

function getFileIcon(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return iconMap[ext] || iconMap["default"];
}

module.exports = { getFileIcon };
