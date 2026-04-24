"""Utility functions for code processing."""

import re
from typing import Optional


def chunk_code(content: str, file_path: str, chunk_size: int = 60,
               overlap: int = 10) -> list[dict]:
    """
    Split code into overlapping chunks for embedding.

    Each chunk contains metadata about its location in the file.
    Uses line-based chunking to preserve code structure.
    """
    lines = content.split("\n")
    chunks = []

    if len(lines) <= chunk_size:
        # Small file — single chunk
        chunks.append({
            "content": content,
            "file_path": file_path,
            "start_line": 1,
            "end_line": len(lines),
            "chunk_index": 0,
        })
        return chunks

    start = 0
    chunk_index = 0

    while start < len(lines):
        end = min(start + chunk_size, len(lines))
        chunk_lines = lines[start:end]
        chunk_content = "\n".join(chunk_lines)

        chunks.append({
            "content": chunk_content,
            "file_path": file_path,
            "start_line": start + 1,  # 1-indexed
            "end_line": end,
            "chunk_index": chunk_index,
        })

        start += chunk_size - overlap
        chunk_index += 1

    return chunks


def extract_imports_simple(content: str, language: str) -> list[str]:
    """
    Extract import statements from code using regex.
    Fallback when tree-sitter is not available for a language.
    """
    imports = []

    if language == "python":
        # Match: import x, from x import y
        patterns = [
            r"^import\s+(\S+)",
            r"^from\s+(\S+)\s+import",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                imports.append(match.group(1))

    elif language in ("javascript", "typescript"):
        # Match: import ... from 'x', require('x')
        patterns = [
            r"import\s+.*?from\s+['\"]([^'\"]+)['\"]",
            r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                imports.append(match.group(1))

    elif language == "java":
        pattern = r"^import\s+([\w.]+)\s*;"
        for match in re.finditer(pattern, content, re.MULTILINE):
            imports.append(match.group(1))

    elif language == "go":
        # Single imports
        pattern = r'^import\s+"([^"]+)"'
        for match in re.finditer(pattern, content, re.MULTILINE):
            imports.append(match.group(1))
        # Block imports
        block_pattern = r'import\s*\((.*?)\)'
        for match in re.finditer(block_pattern, content, re.DOTALL):
            for imp in re.findall(r'"([^"]+)"', match.group(1)):
                imports.append(imp)

    return imports


def extract_functions_simple(content: str, language: str) -> list[dict]:
    """
    Extract function definitions using regex.
    Returns list of {name, start_line, end_line, signature}.
    """
    functions = []
    lines = content.split("\n")

    if language == "python":
        pattern = r"^\s*(async\s+)?def\s+(\w+)\s*\(([^)]*)\)"
        for i, line in enumerate(lines):
            match = re.match(pattern, line)
            if match:
                functions.append({
                    "name": match.group(2),
                    "start_line": i + 1,
                    "end_line": _find_block_end(lines, i, language),
                    "signature": line.strip(),
                    "is_async": match.group(1) is not None,
                })

    elif language in ("javascript", "typescript"):
        patterns = [
            r"^\s*(export\s+)?(async\s+)?function\s+(\w+)\s*\(",
            r"^\s*(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\(",
            r"^\s*(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\w*\s*=>\s*",
        ]
        for i, line in enumerate(lines):
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    name = match.group(3)
                    functions.append({
                        "name": name,
                        "start_line": i + 1,
                        "end_line": _find_block_end(lines, i, language),
                        "signature": line.strip(),
                    })
                    break

    return functions


def extract_classes_simple(content: str, language: str) -> list[dict]:
    """Extract class definitions using regex."""
    classes = []
    lines = content.split("\n")

    if language == "python":
        pattern = r"^\s*class\s+(\w+)\s*(\(([^)]*)\))?\s*:"
        for i, line in enumerate(lines):
            match = re.match(pattern, line)
            if match:
                classes.append({
                    "name": match.group(1),
                    "start_line": i + 1,
                    "end_line": _find_block_end(lines, i, language),
                    "bases": match.group(3).split(",") if match.group(3) else [],
                })

    elif language in ("javascript", "typescript", "java"):
        pattern = r"^\s*(export\s+)?(default\s+)?class\s+(\w+)"
        for i, line in enumerate(lines):
            match = re.match(pattern, line)
            if match:
                classes.append({
                    "name": match.group(3),
                    "start_line": i + 1,
                    "end_line": _find_block_end(lines, i, language),
                    "bases": [],
                })

    return classes


def _find_block_end(lines: list[str], start: int, language: str) -> int:
    """Find the approximate end of a code block."""
    if language == "python":
        # Indentation-based
        if start >= len(lines):
            return start + 1
        base_indent = len(lines[start]) - len(lines[start].lstrip())
        for i in range(start + 1, min(start + 200, len(lines))):
            line = lines[i]
            if line.strip() == "":
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= base_indent and line.strip():
                return i
        return min(start + 50, len(lines))
    else:
        # Brace-based
        depth = 0
        found_open = False
        for i in range(start, min(start + 200, len(lines))):
            for ch in lines[i]:
                if ch == "{":
                    depth += 1
                    found_open = True
                elif ch == "}":
                    depth -= 1
                    if found_open and depth == 0:
                        return i + 1
        return min(start + 50, len(lines))


def extract_function_calls(content: str, language: str) -> list[str]:
    """Extract function call names from code."""
    # Match function_name( patterns, excluding keywords
    keywords = {
        "if", "else", "elif", "for", "while", "with", "try", "except",
        "finally", "return", "yield", "raise", "import", "from", "as",
        "class", "def", "print", "len", "range", "str", "int", "float",
        "list", "dict", "set", "tuple", "type", "isinstance", "hasattr",
        "getattr", "setattr", "super", "self", "cls",
    }
    pattern = r"\b([a-zA-Z_]\w*)\s*\("
    calls = set()
    for match in re.finditer(pattern, content):
        name = match.group(1)
        if name not in keywords and not name[0].isupper():
            calls.add(name)
    return list(calls)
