# Loopy

A utility to run commands in a loop in a persistent, durable way.

## Installation

pip: `pip install loopy`

pipx: `pipx install loopy`

uv: `uv pip install loopy`

uvx: `uvx loopy`

## How it works
- Loops are defined with an ID and a saved command.
- Loop items are ingested from standard input.
- Normally, the loop runs as if running a `while ... ; do ... ; done` loop.
- If unsuccessful, execution is stopped.
  The next invocation of Loopy will continue with the last iteration.
  Alternatively, Loopy can continue with all iterations regardless of command status, and future iterations will only re-run the failed items.

## Example Commands

```bash
# Create a loop
echo -e "file1.txt\nfile2.txt\nfile3.txt" | loopy --id process-files create cat {}

# Run the loop
loopy --id process-files run

# List loops
loopy list

# Continue on failure when running
loopy --id process-files run --continue-on-failure

# Resume a previously failed loop
loopy --id process-files run

# Start over from beginning
loopy --id process-files reset

# Modify loop command
loopy --id process-files cmd dd if={}

# Make a copy of another loop
loopy --id process-files-2 copy-from process-files

# Cancel a loop
loopy --id process-files delete
```
