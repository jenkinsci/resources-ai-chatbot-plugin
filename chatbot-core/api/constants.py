"""Constants shared across the ``api`` package.

Keeping these in a single module avoids the drift that happens when the same
literal is copy-pasted into several files.
"""

# Matches the placeholder tokens that the chunking pipeline substitutes for
# fenced code blocks, e.g. ``[[CODE_BLOCK_0]]`` or ``[[CODE_SNIPPET_3]]``.
# The capture group is the index of the block inside the chunk's ``code_blocks``.
CODE_BLOCK_PLACEHOLDER_PATTERN = r"\[\[(?:CODE_BLOCK|CODE_SNIPPET)_(\d+)\]\]"
