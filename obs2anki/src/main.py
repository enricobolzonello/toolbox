import json
import os
import urllib.request
import argparse
from parsing import bfs
import sys
import tempfile
import time
import glob

TEMP_DIR = tempfile.gettempdir()
TEMP_FILE = os.path.join(TEMP_DIR, "obs2anki_cards.txt")

def cleanup_old_temp_files(temp_dir, pattern="obs2anki_cards_*.txt", max_age_seconds=300):
    now = time.time()
    for filepath in glob.glob(os.path.join(temp_dir, pattern)):
        try:
            mtime = os.path.getmtime(filepath)
            age = now - mtime
            if age > max_age_seconds:
                os.remove(filepath)
                print(f"🗑️ Removed old temp file: {filepath}")
        except Exception as e:
            print(f"⚠️ Failed to remove {filepath}: {e}")


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
    cleanup_old_temp_files(TEMP_DIR)
    parser = argparse.ArgumentParser(
        prog="obs2anki",
        description="Starting from a base note, it parses all connected Obsidian notes "
                    "and extracts flashcards which are then exported to Anki.",
        usage="%(prog)s <filename> <vault_path>"
    )

    parser.add_argument(
        "filename",
        help="File name of the starting note (with or without the .md extension)"
    )

    parser.add_argument(
        "vault_path",
        help="Path to the root of the Obsidian vault"
    )

    args = parser.parse_args()

    if not args.filename.endswith(".md"):
        args.filename += ".md"

    args.vault_path = os.path.expanduser(args.vault_path)
    if not os.path.isdir(args.vault_path):
        print(f"❌ Error: The path '{args.vault_path}' is not a valid directory.")
        sys.exit(1)

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

if __name__ == "__main__":
    main()
