#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import argparse
import pyperclip
import random

rnd = random.SystemRandom()

def init_current():
    result = []
    for i in range(1, 17):
        result.append({"title": f"Бой {i}", "players": []})
    return result

def format_current(current):
    result = []
    for match in current:
        result.extend([match["title"], ""] + match["players"] + ["", ""])
    return "\n".join(result)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", default="shuffle.json")
    args = parser.parse_args()

    if os.path.isfile(args.filename):
        with open(args.filename) as f:
            current = json.load(f)
    else:
        current = init_current()

    basket = pyperclip.paste()
    players = [x.strip() for x in basket.split("\n") if x.strip()]
    rnd.shuffle(players)
    for match, player in zip(current, players):
        match["players"].append(player)

    formatted = format_current(current)
    pyperclip.copy(formatted)
    print(formatted)

    save_data = input("save data? Y/n ")
    if (save_data or "Y") == "Y":
        with open(args.filename, "w") as f:
            json.dump(current, f, indent=4, sort_keys=True, ensure_ascii=False)

if __name__ == "__main__":
    main()
