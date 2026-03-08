import os
import sys

def search_memory(keyword: str, base_paths: list[str], context_lines: int = 3):
    results = []
    for base_path in base_paths:
        if not os.path.exists(base_path):
            continue

        for root, _, files in os.walk(base_path):
            for file_name in files:
                if file_name.endswith('.md'):
                    file_path = os.path.join(root, file_name)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if keyword.lower() in line.lower():
                                start_line = max(0, i - context_lines)
                                end_line = min(len(lines), i + context_lines + 1)
                                
                                snippet = "".join(lines[start_line:end_line])
                                results.append({
                                    "path": file_path,
                                    "line_number": i + 1,
                                    "snippet": snippet.strip()
                                })
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 memory_retriever.py \"<keyword>\"")
        sys.exit(1)

    keyword = sys.argv[1]
    base_directories = ["vault/intelligence", "memory"]
    context_lines = 3

    print(f"Searching for \"{keyword}\" in {base_directories} with {context_lines} lines of context...")
    retrieved_memory = search_memory(keyword, base_directories, context_lines)

    if retrieved_memory:
        for item in retrieved_memory:
            print(f"\n--- Source: {item['path']} #L{item['line_number']} ---")
            print(item['snippet'])
    else:
        print("No relevant memories found.")
