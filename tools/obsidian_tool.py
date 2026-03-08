import json
import os
from typing import Optional, List, Dict, Any
from crewai.tools import BaseTool

class ObsidianTool(BaseTool):
    name: str = "Obsidian Tool"
    description: str = "Interact with an Obsidian vault using direct file operations (Headless Mode). Supported commands: append_content(path, content), read_note(path), search_notes(query)."
    vault_path: str = "/data/.openclaw/workspace/vault"

    def _run(self, command: str, path: str = None, content: str = None, query: str = None, **kwargs) -> str:
        """
        Execute an Obsidian vault operation.
        Args:
            command: The command to execute (append_content, read_note, search_notes).
            path: The relative path to the note (for append/read).
            content: The content to append (for append).
            query: The search query (for search).
        """
        # Handle nested kwargs if LLM wraps them (common issue)
        if kwargs.get('kwargs'):
            nested = kwargs.get('kwargs')
            if isinstance(nested, dict):
                path = nested.get('path', path)
                content = nested.get('content', content)
                query = nested.get('query', query)

        try:
            # Dispatch commands
            if command == "append_content":
                return self.append_content(path, content)
            elif command == "read_note":
                return self.read_note(path)
            elif command == "search_notes":
                return self.search_notes(query)
            else:
                return f"Error: Unknown command '{command}'. Supported: append_content, read_note, search_notes."

        except Exception as e:
            return f"ObsidianTool Error: {str(e)}"

    def append_content(self, relative_path: str, content: str) -> str:
        """Appends content to a markdown file in the vault."""
        if not relative_path or not content:
            return "Error: 'path' and 'content' are required for append_content."
            
        full_path = os.path.join(self.vault_path, relative_path)
        
        # Security check: Ensure path is within vault
        if not os.path.abspath(full_path).startswith(os.path.abspath(self.vault_path)):
             return "Error: Access denied. Path must be inside the vault."

        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "a", encoding="utf-8") as f:
                f.write(content + "\n")
            return f"Success: Appended to {relative_path}"
        except Exception as e:
            return f"Error appending file: {str(e)}"

    def read_note(self, relative_path: str) -> str:
        """Reads a markdown file from the vault."""
        if not relative_path:
            return "Error: 'path' is required for read_note."
        full_path = os.path.join(self.vault_path, relative_path)
        
        # Security check: Ensure path is within vault
        if not os.path.abspath(full_path).startswith(os.path.abspath(self.vault_path)):
             return "Error: Access denied. Path must be inside the vault."
        
        if not os.path.exists(full_path):
            return "Error: File not found."
            
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def search_notes(self, query: str) -> str:
        """Simple grep-like search in the vault."""
        if not query:
             return "Error: 'query' is required for search_notes."
        results = []
        try:
            for root, dirs, files in os.walk(self.vault_path):
                for file in files:
                    if file.endswith(".md"):
                        path = os.path.join(root, file)
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            if query.lower() in content.lower():
                                rel_path = os.path.relpath(path, self.vault_path)
                                results.append(rel_path)
            return "\n".join(results) if results else "No matches found."
        except Exception as e:
            return f"Error searching notes: {str(e)}"
