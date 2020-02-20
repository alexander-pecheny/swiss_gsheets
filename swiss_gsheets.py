#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import itertools
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import networkx as nx

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


class TransformedRange(dict):
    def __init__(self, cells):
        self._cells = cells
        self.header_row = [c for c in cells if c.row == 1]
        for cell in self.header_row:
            self[cell.value.strip()] = [
                x for x in self._cells if x.col == cell.col and x.row != 1
            ]


def values(cells):
    return [x.value for x in cells]


class SwissSystem:
    def __init__(self, config):
        self.config = config
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self.config["keyfile_path"], SCOPE
        )
        gc = gspread.authorize(credentials)
        self.table = gc.open_by_key(self.config["table_key"])
        sheets = self.table.worksheets()
        self.rounds_sheet = [
            x for x in sheets if x.title == self.config["team_sheet_name"]
        ][0]
        rounds_range = self.load_rounds_range()
        teams = values(rounds_range[self.config["team_column_name"]])
        initial_seeding = values(
            rounds_range[self.config["seeding_column_name"]]
        )
        self.teams = [
            {
                "team_name": team,
                "initial_seeding": float(is_),
                "points": [],
                "points_additional": [],
                "opponents_points": [],
                "opponents_points_additional": [],
                "opponents": set(),
            }
            for (team, is_) in zip(teams, initial_seeding)
        ]
        self.combs = set(itertools.combinations(sorted(teams), 2))
        self.teams_by_name = {x["team_name"]: x for x in self.teams}
        self.pairings = []
        self.round = 0

    def load_rounds_range(self):
        return TransformedRange(
            self.rounds_sheet.range(self.config["rounds_range"])
        )

    @staticmethod
    def get_total_points(x):
        return (
            sum(x["points"])
            + 0.1 * sum(x["points_additional"])
            + 0.01 * sum(x["opponents_points"])
            + 0.001 * sum(x["opponents_points_additional"])
        )

    @staticmethod
    def sorted_pair(pair):
        if pair[0] <= pair[1]:
            return pair
        return (pair[1], pair[0])

    def next_round(self):
        if self.round == 0:
            is_sorted = sorted(self.teams, key=lambda x: x["initial_seeding"])
            pairings = list(zip(is_sorted[::2], is_sorted[1::2]))
            pairings = [
                self.sorted_pair((pair[0]["team_name"], pair[1]["team_name"]))
                for pair in pairings
            ]
            for pair in pairings:
                print("{} - {}".format(pair[0], pair[1]))
                self.combs.remove(pair)
            self.round += 1
            self.pairings.append(pairings)
            return pairings
        else:
            trange = self.load_rounds_range()
            points = self.get_points(trange)
            this_round_pairings = {
                x[0]: x[1] for x in self.pairings[self.round - 1]
            }
            this_round_pairings.update(
                {x[1]: x[0] for x in self.pairings[self.round - 1]}
            )
            for team in self.teams:
                name = team["team_name"]
                ps, aps = points[name]
                team["points"].append(ps)
                team["points_additional"].append(aps)
                opponent_name = this_round_pairings[name]
                ops, oaps = points[opponent_name]
                team["opponents_points"].append(ops)
                team["opponents_points_additional"].append(oaps)
                team["opponents"].add(opponent_name)
            g = nx.Graph()
            for comb in self.combs:
                g.add_edge(
                    comb[0],
                    comb[1],
                    weight=1000
                    - abs(
                        self.get_total_points(self.teams_by_name[comb[0]])
                        - self.get_total_points(self.teams_by_name[comb[1]])
                    ),
                )
            matching = nx.max_weight_matching(g)
            next_round_pairings = []
            for pair in matching:
                next_round_pairings.append(self.sorted_pair(pair))
                self.combs.remove(self.sorted_pair(pair))
            for pair in sorted(
                next_round_pairings,
                key=lambda p: self.get_total_points(self.teams_by_name[p[0]])
                + self.get_total_points(self.teams_by_name[p[1]]),
                reverse=True,
            ):
                print(
                    "{} ({}) - {} ({})".format(
                        pair[0],
                        self.get_total_points(self.teams_by_name[pair[0]]),
                        pair[1],
                        self.get_total_points(self.teams_by_name[pair[1]]),
                    )
                )
            if len(self.combs) == 0:
                print("all combinations are exhausted!")
            self.round += 1
            self.pairings.append(next_round_pairings)
            return next_round_pairings

    @staticmethod
    def wrapfloat(x):
        return float(x.replace(",", "."))

    def get_points(self, trange):
        teams = trange["Команда"]
        points = trange["{} тур".format(self.round)]
        points_additional = trange['{} тур "+"'.format(self.round)]
        return {
            x[0]: (self.wrapfloat(x[1]), self.wrapfloat(x[2]))
            for x in zip(
                values(teams), values(points), values(points_additional)
            )
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    ss = SwissSystem(config)

    while True:
        print("Press Enter to generate new pairs...")
        _ = input()
        ss.next_round()


if __name__ == "__main__":
    main()
