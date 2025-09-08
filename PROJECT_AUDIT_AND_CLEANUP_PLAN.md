# Project Audit & Cleanup Plan

## 1. Introduction

This document outlines a full audit of the ZenGlow project. The project is currently in a difficult state due to significant clutter, duplicated files, and misconfigurations. The goal of this plan is to establish a clean, maintainable, and stable codebase.

## 2. Core Problem: Duplicated Project Structure

The fundamental issue is that the repository contains two separate projects:

*   **Root Project (`/`):** A modern Expo Router-based project.
*   **Legacy Project (`/ZenGlow`):** An older, classic React Native or Expo project.

This has resulted in widespread duplication of components, assets, configurations, and Supabase logic, making the project nearly impossible to manage.

**Primary Recommendation:** Establish the **root directory** as the single source of truth and completely remove the legacy `/ZenGlow` directory after migrating any essential files.

---

## 3. Detailed Audit Findings

### 3.1. Project Structure & File Organization

*   **Issue:** Component directories exist in `/components`, `/ZenGlow/components`, and `/ZenGlow/src/components`.
*   **Issue:** Asset files (sounds, images) are scattered across `/assets/sound-drop`, `/ZenGlow/audio-drop`, and `/ZenGlow/src/assets/sounds`.
*   **Issue:** Supabase configurations are duplicated in `/supabase` and `/ZenGlow/supabase`.
*   **Recommendation:** Consolidate all code and assets into a unified structure within the root project (e.g., `/app`, `/components`, `/assets`).

### 3.2. Configuration Files

*   **Issue:** Multiple Babel configs (`.babelrc`, `babel.config.js`), Metro configs, ESLint/Prettier configs, and `.gitignore` files exist.
*   **Recommendation:** Consolidate all configurations into single, standard files in the project root. For example, use one `babel.config.js`, one `metro.config.js`, and one `.eslintrc.cjs`.

### 3.3. Code Quality (Example: `ZenSoundProvider.tsx`)

*   **Issue:** Brittle and confusing asset paths (e.g., `require('../../audio-drop/...')`).
*   **Issue:** Use of a global variable (`(global as any).zenSound = ...`), which is an anti-pattern in React. State should be managed via context or state management libraries.
*   **Issue:** Unclear state logic that could be simplified and made more readable using standard React hooks like `useEffect`.
*   **Recommendation:** Refactor components to use correct asset paths, remove global variables in favor of React context, and follow standard React patterns.

---

## 4. Step-by-Step Action Plan

**Step 0: Backup Your Project!**
*Commit your current work and/or create a zip archive of the entire directory before proceeding.*

**Step 1: Clean the Project Structure**
*   Manually review the `/ZenGlow` directory.
*   Move any unique, necessary files (components, assets, docs) into the main project structure at the root.
*   Delete the entire `/ZenGlow` directory: `rm -rf ./ZenGlow`

**Step 2: Consolidate Configuration**
*   Delete all redundant configuration files from the root and subdirectories.
*   Create single, correct configuration files in the root for Babel, Metro, ESLint, and Prettier.
*   Merge the two `.gitignore` files into one comprehensive file in the root.

**Step 3: Organize Assets**
*   Create a single, well-structured assets directory (e.g., `assets/sounds`, `assets/images`).
*   Move all sound and image files into this new directory, organizing them into sub-folders.

**Step 4: Refactor and Fix Code**
*   Go through your components and update all `require` paths to point to the new, consolidated `assets` directory.
*   Refactor code to address quality issues, starting with components like `ZenSoundProvider.tsx`.

**Step 5: Install Dependencies and Test**
*   Remove the old `node_modules` directory: `rm -rf node_modules`
*   Perform a clean install: `npm install`
*   Run the app with a cleared cache to ensure everything works: `npx expo start --clear`

---

## 5. Conclusion

Following this plan will resolve the current structural and configuration issues, resulting in a project that is significantly easier to develop, debug, and maintain.
