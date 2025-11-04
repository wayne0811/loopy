# Loopy Design Document

## Overview
Loopy is a Python utility for running commands in a persistent, durable loop with failure recovery capabilities.

## Architecture

### CLI Framework
- **Click**: Used for command-line interface and argument parsing
- Provides clean command structure and help documentation
- Handles input validation and type conversion

### Persistence Layer
- **SQLite**: Primary database for storing loop state and progress
- Database abstraction layer to support future database backends
- Stores loop definitions, execution state, and failed items

### Core Components

#### Loop Manager
- Manages loop lifecycle (create, resume, cleanup)
- Tracks execution progress and failure state
- Handles command execution with subprocess

#### Database Schema
```sql
loops (id, command, created_at, status)
loop_items (loop_id, item, status, attempts, last_error)
```

#### Command Execution
- Subprocess-based command execution
- Error capture and logging

## Testing Strategy
- **pytest**: Primary testing framework
- Unit tests for core components
- Integration tests for CLI commands
- Mock subprocess calls for command execution tests
- Temporary SQLite databases for test isolation

## Configuration
- Default SQLite database location: `$XDG_CONFIG_HOME/.loopy/db.sqlite`
- Configurable via environment variables or CLI flags
