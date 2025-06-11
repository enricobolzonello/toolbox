import os
from collections import deque
import re

FLASHCARD_PATTERN = r"#\[flashcard\]\s*Q:\s*(.*?)\s*A:\s*(.*?)(?=\n#\[flashcard\]|\Z)"

def get_after_select_connection(text):
    keyword = "Select Connection:"
    index = text.find(keyword)
    if index == -1:
        return text
    newline_index = text.find("\n", index)
    return text[newline_index + 1 :] if newline_index != -1 else ""


def find_file(filename, vault_path):
    for root, dirs, files in os.walk(vault_path):
        if filename in files:
            return os.path.join(root, filename)
    return None


def bfs(root_file, vault_path):
    start_file = find_file(root_file, vault_path)
    if not start_file:
        raise FileNotFoundError(f"Starting file '{root_file}' not found in '{vault_path}'")

    q = deque([start_file])
    cards = []
    visited = set([start_file])

    while q:
        node_path = q.popleft()
        flashcards, new_nodes = parse_file(node_path, vault_path)
        cards.extend(flashcards)
        for n in new_nodes:
            if n not in visited:
                q.append(n)
                visited.add(n)
    return cards


def parse_file(file_path, vault_path):
    file_path = os.path.expanduser(file_path)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = get_after_select_connection(f.read())
        card_matches = re.findall(FLASHCARD_PATTERN, content, re.DOTALL)

        raw_links = re.findall(r"\[\[(.*?)\]\]", content)
        note_names = []
        for raw_link in raw_links:
            # Remove everything after | or #
            clean_name = re.split(r"[#|]", raw_link)[0].strip()
            if not clean_name.endswith(".md"):
                clean_name += ".md"
            note_names.append(clean_name)

        file_matches = []
        for name in note_names:
            path = find_file(name, vault_path)
            if path is None:
                print(f"⚠️  Could not find linked note: '{name}'")
            else:
                file_matches.append(path)
     

    return card_matches, file_matches