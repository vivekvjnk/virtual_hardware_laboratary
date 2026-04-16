# Repository Overview

Welcome to the **Virtual Hardware Laboratary (VHL)** agent backend. This repository contains the core logic, agents, and orchestration systems for building and managing virtual hardware using AI agents.

## Project Structure

The codebase is organized into several key components:

### 1. Agent Orchestration (`aosm/`)
The **Agent Orchestration State Machine (AOSM)** is the "brain" of the system. It coordinates the tasks and transitions between different specialized agents to achieve complex hardware design goals.

### 2. Archy Agent (`archy/`)
**Archy** is responsible for component synthesis and design. It specializes in generating **SCUD** (System Component Under Design) documents, which describe the hardware architecture and components.

### 3. Analysis Agent (`ana/`)
The **Ana** agent and its workers focus on analyzing the current state of the workspace. This includes vision-based analysis, error correction, and synthesis of technical documents.

### 4. Librarian Agent (`librarian/`)
The **Librarian** agent manages the repository of knowledge and resources required by other agents during the design process.

### 5. VHL Protocol (`vhl_protocol/`)
A shared library containing the communication protocols and data models used across all VHL components.

### 6. Workspace Management (`vhl_workspace/` & `workspace/`)
Handles the environment where agents operate, including file management and tool access.

## Technology Stack

- **Python**: Core programming language.
- **uv**: Modern Python package and project manager.
- **Sphinx**: Documentation generation with `myst-parser` for Markdown support.
- **OpenHands SDK**: Framework for building autonomous AI agents.
- **LLMs**: Integration with state-of-the-art models like Gemini and Claude for reasoning and generation.

## Getting Started

To set up the development environment:

1. Install `uv` if you haven't already.
2. Run `uv sync` to install dependencies.
3. Use `uv run` to execute agents or orchestration scripts.

For more detailed information, please refer to the specific agent directories.
