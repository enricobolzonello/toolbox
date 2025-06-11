import json
import os
import urllib.request
import argparse
from parsing import bfs

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
