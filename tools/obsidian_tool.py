import os
from typing import Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class ObsidianToolSchema(BaseModel):
    command: str = Field(..., description="The command to execute: 'append_content', 'read_note', or 'search_notes'.")
    path: Optional[str] = Field(None, description="The relative path to the note (e.g., 'vault/notes/idea.md'). Required for append_content and read_note.")
    content: Optional[str] = Field(None, description="The content to append. Required for append_content.")
    query: Optional[str] = Field(None, description="The search query. Required for search_notes.")

class ObsidianTool(BaseTool):
    name: str = "Obsidian Tool"
    description: str = "Interact with an Obsidian vault using direct file operations (Headless Mode). Supported commands: append_content(path, content), read_note(path), search_notes(query)."
    args_schema: type[BaseModel] = ObsidianToolSchema

    def _run(self, command: str, path: Optional[str] = None, content: Optional[str] = None, query: Optional[str] = None, **kwargs) -> str:
        vault_path = "vault"  # Default vault path
        
        try:
            if command == "append_content":
                if not path or not content:
                    return "Error: 'path' and 'content' are required for append_content."
                
                full_path = os.path.join(vault_path, path.replace("vault/", ""))
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                with open(full_path, "a", encoding="utf-8") as f:
                    f.write("\n" + content + "\n")
                return f"Success: Appended content to {path}"
                
            elif command == "read_note":
                if not path:
                    return "Error: 'path' is required for read_note."
                
                full_path = os.path.join(vault_path, path.replace("vault/", ""))
                if not os.path.exists(full_path):
                    return f"Error: File {path} not found."
                
                with open(full_path, "r", encoding="utf-8") as f:
                    return f.read()
                    
            elif command == "search_notes":
                if not query:
                    return "Error: 'query' is required for search_notes."
                
                results = []
                for root, dirs, files in os.walk(vault_path):
                    for file in files:
                        if file.endswith(".md"):
                            file_path = os.path.join(root, file)
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                if query.lower() in f.read().lower():
                                    results.append(file_path)
                return "\n".join(results) if results else "No matches found."
            
            else:
                return f"Error: Unknown command '{command}'"
                
        except Exception as e:
            return f"Error executing ObsidianTool: {str(e)}"

if __name__ == "__main__":
    # Test
    tool = ObsidianTool()
    print(tool._run(command="append_content", path="test_note.md", content="Hello World"))
