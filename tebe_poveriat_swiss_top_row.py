#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from gspread.models import Cell
from gspread_formatting import (
    DataValidationRule,
    BooleanCondition,
    batch_updater,
)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    "Studchr-9a61ec5b422c.json", scope
)
gc = gspread.authorize(credentials)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table_id", "-t")
    parser.add_argument("-u", action="store_true")
    args = parser.parse_args()

    spreadsheet = gc.open_by_key(args.table_id)
    if args.u:
        sheet = spreadsheet.worksheet("Утешительная швейцарка")
    else:
        sheet = spreadsheet.worksheet("Швейцарка")
    row = 2
    col = 3
    update_cells = []
    if args.u:
        vlookup_list = (None, 3, 2, 81, 76, 77, 78, 79, 80)
    else:
        vlookup_list = (None, 3, 2, 57, 52, 53, 54, 55, 56)
    if args.u:
        rounds = [5, 6, 7]
    else:
        rounds = [1, 2, 3, 4]
    for round in rounds:
        for vcol in vlookup_list:
            if vcol:
                if args.u:
                    value = f"=VLOOKUP($A2, 'Круг {round} (утешительный, протокол)'!$B$1:$CD$112, {vcol}, FALSE)"
                else:
                    value = f"=VLOOKUP($A2, 'Круг {round} (протокол)'!$B$1:$BF$112, {vcol}, FALSE)"
                update_cells.append(Cell(row, col, value))
            col += 1
    sheet.update_cells(update_cells, value_input_option="USER_ENTERED")


if __name__ == "__main__":
    main()
