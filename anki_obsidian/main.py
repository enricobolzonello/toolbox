import json
from collections import deque
import re
import os
from os.path import expanduser, dirname
import urllib.request
import argparse

FLASHCARD_PATTERN = r"#\[flashcard\]\s*Q:\s*(.*?)\s*A:\s*(.*?)(?=\n#\[flashcard\]|\Z)"


def request(action, **params):
    return {"action": action, "params": params, "version": 6}


def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode("utf-8")
    response = json.load(
        urllib.request.urlopen(
            urllib.request.Request("http://127.0.0.1:8765", requestJson)
        )
    )
    if len(response) != 2:
        raise Exception("response has an unexpected number of fields")
    if "error" not in response:
        raise Exception("response is missing required error field")
    if "result" not in response:
        raise Exception("response is missing required result field")
    if response["error"] is not None:
        raise Exception(response["error"])
    return response["result"]


# invoke('createDeck', deck='test1')
# result = invoke('deckNames')
# print('got list of decks: {}'.format(result))

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
        print(flashcards, new_nodes)
        cards.extend(flashcards)
        for n in new_nodes:
            if n not in visited:
                q.append(n)
                visited.add(n)
    return cards


def parse_file(file_path, vault_path):
    file_path = expanduser(file_path)
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



def main():
    parser = argparse.ArgumentParser(
        prog="Obsidian->Anki flashcards",
        description="Starting from a base note, it parses all connected obsidian notes and extracts flashcards which are then exported to Anki",
    )
    parser.add_argument("filename")
    parser.add_argument("vault_path")
    args = parser.parse_args()

    cards = bfs(args.filename, args.vault_path)
    if not cards:
        print("⚠️  No flashcards found.")
    else:
        print("✅ Found flashcards:")
        for q, a in cards:
            print(f"Q: {q.strip()} \nA: {a.strip()}\n")



if __name__ == "__main__":
    main()
