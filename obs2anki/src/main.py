import json
import os
import urllib.request
import argparse
from parsing import bfs

TEMP_FILE = os.path.dirname(__file__) + '/cards.txt'

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

    deck_names = invoke('deckNames')
    existing_notes = set()
    if args.filename not in deck_names:
        invoke('createDeck', deck=args.filename)
        print(f"✅  Creating new deck {args.filename}.")
    else:
        result = invoke('notesInfo', query=f"deck:{args.filename}")
        for existing_note in result:
            question = existing_note["fields"]["Front"]["value"]
            answer = existing_note["fields"]["Back"]["value"]

            for q, a in cards:
                note_id = existing_note["noteId"]
                
                if q==question and a==answer:
                    existing_notes.add((q, a))
                elif q == question or a == answer:
                    new_front = question if q != question else q
                    new_back = answer if a != answer else a

                    print(f"⚠️  Updating note with new front {new_front} and back {new_back}.")
                    
                    invoke("updateNoteFields", note={
                        "id": note_id,
                        "fields": {
                            "Front": new_front,
                            "Back": new_back
                        }
                    })
                    existing_notes.add((q, a))


    with open(TEMP_FILE, 'w') as f:   
        f.write(f"#deck:{args.filename}\n")
        count = 0
        for q,a in cards:
            if (q,a) in existing_notes:
                continue
            f.write(f"{q};{a}\n")
            count += 1
    if count > 0:
        invoke('guiImportFile', path=TEMP_FILE)
    else:
        print("⚠️  Skipping empty file.")
    os.remove(TEMP_FILE)

if __name__ == "__main__":
    main()
