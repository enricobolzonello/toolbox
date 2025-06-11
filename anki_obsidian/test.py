import json
from collections import deque
import re
from os.path import expanduser, dirname
import urllib.request

FLASHCARD_PATTERN = r"#\[flashcard\]\s*Q:\s*(.*?)\s*A:\s*(.*?)(?=\n#\[flashcard\]|\Z)"

def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

#invoke('createDeck', deck='test1')
#result = invoke('deckNames')
#print('got list of decks: {}'.format(result))
def get_after_select_connection(text):
    keyword = "Select Connection:"
    index = text.find(keyword)
    if index == -1:
        return ""  # or return full text if you prefer
    # Move to the end of that line
    newline_index = text.find('\n', index)
    return text[newline_index + 1:] if newline_index != -1 else ""

def bfs(root_path):
    q = deque([])
    q.append(root_path)
    cards = []
    visited = set([root_path])
    while q:
        node_path = q.popleft()
        flashcards, new_nodes = parse_file(node_path)
        print(flashcards, new_nodes)
        cards.extend(flashcards)
        for n in new_nodes:
            if n not in visited:
                q.append(n)
                visited.add(n)
    return cards

def parse_file(file_path):
    file_path = expanduser(file_path)
    base_name = dirname(file_path)
    file_matches = [] 
    with open(file_path, "r") as f:
        content = get_after_select_connection(f.read())
        card_matches = re.findall(FLASHCARD_PATTERN, content, re.DOTALL)
        file_matches = [base_name+"/"+file_name+".md" for file_name in re.findall(r"\[\[(.*?)\]\]", content)]
    return card_matches, file_matches

def main():
    parser = argparse.ArgumentParser(prog="Obsidian->Anki flashcards", description="Starting from a base note, it parses all connected obsidian notes and extracts flashcards which are then exported to Anki")
    parser.add_argument(filename)
    args = parser.parse_args()

    bfs(args.filename)
