#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import argparse
import json
import math
import random
from collections import Counter, defaultdict
from itertools import combinations
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from gspread.models import Cell
import networkx as nx
import pyperclip

rnd = random.SystemRandom()

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


class SwissGenerator:
    def __init__(self, args):
        self.args = args
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self.args.credentials, scope
        )
        self.gs = gspread.authorize(credentials)
        self.table = self.gs.open_by_key(self.args.table)
        self.clip_result = []
        self.played_with_each_other = Counter()
        self.uteshit_rows = None

    @classmethod
    def normalize_comb(cls, tup_):
        return (min(tup_), max(tup_))

    @classmethod
    def generate_combs(cls, list_):
        return {cls.normalize_comb(x) for x in combinations(list_, 2)}

    def get_swiss_data_prod(self):
        wks = self.table.worksheet("Швейцарка")
        rows = wks.get_all_records()
        if self.args.round >= 5:
            wks2 = self.table.worksheet("Утешительная швейцарка")
            self.uteshit_rows = wks2.get_all_records()
            rows.extend(self.uteshit_rows)
        return rows

    def get_swiss_data_debug(self):
        with open(f"debug_swiss.json") as f:
            result = json.load(f)
        return result

    def read_results(self):
        if self.args.mode == "prod":
            rows = self.get_swiss_data_prod()
        elif self.args.mode == "debug":
            rows = self.get_swiss_data_debug()
        self.players_data = defaultdict(dict)
        for r in rows:
            if not r["Игрок"]:
                continue
            self.players_data[r["Игрок"]].update(r)
        self.points = Counter()
        for p in self.players_data:
            data = self.players_data[p]
            for r in range(1, self.args.round):
                if f"Круг {r} место" not in data:
                    continue
                self.points[p] += (
                    4
                    - (data[f"Круг {r} место"] or 4)
                    + max(0, data[f"Круг {r} очки"] / 100)
                    + 0.0001 * max(0, data[f"Круг {r} в плюс"])
                    + 0.000001 * data[f"Круг {r} 50"]
                    + 0.00000001 * data[f"Круг {r} 40"]
                    + 0.0000000001 * data[f"Круг {r} 30"]
                    + 0.000000000001 * data[f"Круг {r} 20"]
                    + 0.00000000000001 * data[f"Круг {r} 10"]
                )
        if self.args.round <= 4:
            self.available_pairs = self.generate_combs(list(self.players_data.keys()))
        else:
            uteshit_players = sorted(
                [r["Игрок"] for r in self.uteshit_rows if r["Игрок"]],
                key=lambda x: self.points[x],
                reverse=True,
            )
            used_dummies = {
                r["Игрок"] for r in self.table.worksheet("Болваны").get_all_records()
            }
            dummies = []
            if len(uteshit_players) % 4:
                n_dummies = 4 * math.ceil(len(uteshit_players) / 4) - len(
                    uteshit_players
                )
                batch_len = math.ceil(len(uteshit_players) / n_dummies)
                up = uteshit_players.copy()
                for i in range(n_dummies):
                    batch, up = up[:batch_len], up[batch_len:]
                    dummy_source = rnd.choice(batch)
                    while dummy_source in used_dummies:
                        dummy_source = rnd.choice(batch)
                    dummy_name = f"Болван {self.args.round}-{i + 1}"
                    print(f"Создаём болвана {dummy_name} — клона {dummy_source}")
                    dummies.append(dummy_name)
                    self.points[dummy_name] = self.points[dummy_source]
            uteshit_players.extend(dummies)
            self.available_pairs = self.generate_combs(uteshit_players)

    def get_debug_players_values(self, round):
        with open(f"debug_round_{round}.json") as f:
            result = json.load(f)
        return result

    def read_used_pairings(self):
        rounds = list(range(1, self.args.round))
        for r in rounds:
            if self.args.mode == "prod":
                u = "утешительный, " if r >= 5 else ""
                wks = self.table.worksheet(f"Круг {r} ({u}протокол)")
                column = wks.col_values(2)
            elif self.args.mode == "debug":
                column = self.get_debug_players_values(r)
            matches = []
            current_match = []
            for cell in column:
                value = cell
                if not value.strip() or value.startswith("Круг") or value == "1":
                    continue
                elif value.startswith("Бой"):
                    if current_match:
                        matches.append(current_match)
                        current_match = []
                else:
                    if value not in self.players_data and not value.startswith(
                        "Болван"
                    ):
                        sys.stderr.write(
                            f"Игрок {value} не найден на листе Швейцарка\n"
                        )
                    current_match.append(value)
            for match in matches:
                for comb in self.generate_combs(match):
                    self.played_with_each_other[comb] += 1

    @classmethod
    def count_dummies(cls, list_):
        result = 0
        for element in list_:
            if element.startswith("Болван"):
                result += 1
        return result

    def check_quadruplet(self, quadruplet):
        all_ids = list(quadruplet[0]) + list(quadruplet[1])
        return (
            len(set(all_ids)) == 4
            and sum(
                self.played_with_each_other[x] for x in self.generate_combs(all_ids)
            )
            <= self.args.max_common_games
            and self.count_dummies(all_ids) <= 1
        )

    def get_total_diff(self, quadruplet):
        return abs(
            (self.points[quadruplet[0][0]] + self.points[quadruplet[0][1]]) / 2
            - (self.points[quadruplet[1][0]] + self.points[quadruplet[1][1]]) / 2
        )

    def get_total_points(self, quadruplet):
        return (
            self.points[quadruplet[0][0]]
            + self.points[quadruplet[0][1]]
            + self.points[quadruplet[1][0]]
            + self.points[quadruplet[1][1]]
        )

    def format_quadruplet(self, quadruplet):
        members = list(quadruplet[0]) + list(quadruplet[1])
        return sorted(members, key=lambda x: self.points[x], reverse=True)

    def debug_output_step(self, i, quadruplet):
        match_number = i + 1
        members = sorted(
            list(quadruplet[0]) + list(quadruplet[1]),
            key=lambda x: self.points[x],
            reverse=True,
        )
        points = [self.points[x] for x in members]
        diff_between_pairs = self.get_total_diff(quadruplet)
        result = []
        result.append(f"Бой {match_number}: ")
        self.clip_result.append(f"Бой {match_number}: ")
        result.append(
            f"Состав: "
            + ", ".join(f"{x} ({round(self.points[x], 2)})" for x in members)
        )
        for x in members:
            self.clip_result.append(x)
        self.clip_result.append("")
        self.clip_result.append("")
        result.append(
            f"Сумма очков: {round(sum(points), 2)}, Минимум: {round(min(points), 2)}, Максимум: {round(max(points), 2)}"
        )
        result.append(f"Разница мин/макс: {round(abs(min(points) - max(points)), 2)}")
        result.append(f"Разница между парами: {round(diff_between_pairs, 2)}")
        print("\n".join(result) + "\n\n")

    def generate(self):
        self.read_results()
        self.read_used_pairings()
        g = nx.Graph()
        for p in self.available_pairs:
            if self.played_with_each_other[p] > self.args.max_common_games:
                continue
            g.add_edge(
                p[0],
                p[1],
                weight=10000
                - abs(self.points[p[0]] - self.points[p[1]])
                - self.args.common_games_penalty * self.played_with_each_other[p],
            )
        matching = list(nx.max_weight_matching(g))
        best_pairs = "\n".join(sorted([p[0] + " - " + p[1] for p in matching]))
        print(f"Лучшие пары: {best_pairs}\n")
        quadruplets = [
            x for x in self.generate_combs(matching) if self.check_quadruplet(x)
        ]
        g1 = nx.Graph()
        for q in quadruplets:
            g1.add_edge(q[0], q[1], weight=10000 - self.get_total_diff(q))
        matching2 = sorted(
            list(nx.max_weight_matching(g1)), key=self.get_total_points, reverse=True
        )
        for i, quadruplet in enumerate(matching2):
            self.debug_output_step(i, quadruplet)
        pyperclip.copy("\n".join(self.clip_result))
        print("Результат жеребьёвки скопирован в буфер для вставки.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", "-t", default="")
    parser.add_argument("--credentials", "-c", default="Studchr-9a61ec5b422c.json")
    parser.add_argument("--round", "-r", type=int)
    parser.add_argument("--mode", "-m", choices=["prod", "debug"], default="prod")
    parser.add_argument("--max_common_games", "-mcg", type=int, default=0)
    parser.add_argument("--common_games_penalty", "-cgp", type=int, default=0)
    args = parser.parse_args()
    sg = SwissGenerator(args)
    sg.generate()


if __name__ == "__main__":
    main()
