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
        description="Starting from a base note or a folder, it parses connected Obsidian notes "
                    "and extracts flashcards which are then exported to Anki.",
        usage="%(prog)s <filename_or_directory> <vault_path>"
    )

    parser.add_argument(
        "filename",
        help="File name of the starting note (with or without the .md extension), "
             "or a folder containing multiple notes"
    )

    parser.add_argument(
        "vault_path",
        help="Path to the root of the Obsidian vault"
    )

    args = parser.parse_args()

    args.vault_path = os.path.expanduser(args.vault_path)
    if not os.path.isdir(args.vault_path):
        print(f"❌ Error: The path '{args.vault_path}' is not a valid directory.")
        sys.exit(1)

    flashcard_pairs = []

    target_path = os.path.join(args.vault_path, args.filename[:-1] if args.filename[-1] == "/" else args.filename)
    if os.path.isdir(target_path):
        md_files = [f for f in os.listdir(target_path) if f.endswith(".md")]
        print(f"📁 Processing {len(md_files)} files in directory '{args.filename}'...")
        for md_file in md_files:
            cards = bfs(md_file, args.vault_path)
            flashcard_pairs.extend(cards)
    else:
        if not args.filename.endswith(".md"):
            args.filename += ".md"
        flashcard_pairs = bfs(args.filename, args.vault_path)

    # remove duplicates
    flashcard_pairs = list(set(flashcard_pairs))

    if not flashcard_pairs:
        print("⚠️  No flashcards found.")
        return

    print(f"✅ Found {len(flashcard_pairs)} flashcards:")
    for q, a in flashcard_pairs:
        print(f"Q: {q.strip()} \nA: {a.strip()}\n\n")

    deck_name = args.filename if not os.path.isdir(target_path) else os.path.basename(target_path)
    deck_names = invoke('deckNames')
    existing_notes = set()

    if deck_name not in deck_names:
        invoke('createDeck', deck=deck_name)
        print(f"✅  Creating new deck {deck_name}.")
    else:
        result = invoke('notesInfo', query=f"deck:{deck_name}")
        for existing_note in result:
            question = existing_note["fields"]["Front"]["value"]
            answer = existing_note["fields"]["Back"]["value"]
            note_id = existing_note["noteId"]

            for q, a in flashcard_pairs:
                if q == question and a == answer:
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
        f.write(f"#deck:{deck_name}\n")
        count = 0
        for q, a in flashcard_pairs:
            if (q, a) in existing_notes:
                continue
            f.write(f"{q};{a}\n")
            count += 1

    if count > 0:
        invoke('guiImportFile', path=TEMP_FILE)
    else:
        print("⚠️  Skipping empty file.")


if __name__ == "__main__":
    main()
