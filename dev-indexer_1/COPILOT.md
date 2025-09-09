# Standard Operating Procedures for AI Terminal Co-pilot

**Document Reference:** This SOP governs terminal interaction. For general AI principles and code generation standards, see **.github/copilot-instructions.md** (workspace guardrails). For project structure context, see the **[Architecture Overview](./Architecture_OverView_)**.

---

## 1. Introduction

This document outlines the best practices for working with me, your AI terminal co-pilot. Following these guidelines will ensure our collaboration is safe, efficient, and successful. The procedures are divided into two primary modes of operation: **Manual Step-by-Step** for detailed control and **Autonomous Goal Execution** for speed.

---

## 2. Core Principles

-   **State a Clear Goal:** Always begin by stating a clear, high-level goal. This is the most crucial step.
-   **Provide Project Context:** When the task involves the project, use the **[Architecture Overview (Architecture_OverView_.md)](./Architecture_OverView_.md)** as a map to understand file locations and dependencies.
-   **Safety with Destructive Commands:** For any command that permanently modifies or deletes files (e.g., `rm`, `mv`, `git reset --hard`), I will stop and ask for your explicit confirmation. Please respond with "**Yes**" or "**Confirm**" to proceed.

---

## 3. Modes of Operation

### Mode A: Manual Step-by-Step Execution

This mode is ideal for complex tasks, debugging, or when you want full control over every command.

**Procedure:**
1.  You provide a goal.
2.  I will provide exactly **one** terminal command.
3.  You will run the command.
4.  I will wait to receive the output from the command.
5.  Based on the output, I will provide the next single command. We repeat this until the goal is achieved.

---

### Mode B: Autonomous Goal Execution

This mode is best for routine tasks or when you want the fastest path to completion.

**Procedure:**
1.  You provide a high-level goal using the template below.
2.  I will translate it into the necessary commands.
3.  I will execute them sequentially, reading the output from each one to inform the next, without asking for your intervention.
4.  I will continue this autonomous process until the task is complete.

#### Template for Initiating Autonomous Mode:
