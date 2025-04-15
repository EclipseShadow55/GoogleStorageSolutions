import gspread
from google.oauth2 import service_account
import json
from copy import deepcopy
from gspread import utils as gsutils

# Getting config information
with open("config.json", "r") as f:
    config = json.load(f)

# Setting up Google Sheet storage
SCOPE = ['https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(
    config["service_account_creds_filepath"], scopes=SCOPE)
gc = gspread.authorize(creds)


def normalize_data(values: dict[str, list[str | int]] | list[list[str | int]]):
    """
    Normalizes the data to be in a 2D list format for Google Sheets API.
    :param values: The data to be normalized. It has to be one of the following specific formats:
        - dict: {header1:str: [value1:str, value2:str], header2:str: [value3:str, value4:str]}
        - list: [[value1:str, value2:str], [value3:str, value4:str]]
    :return: Normalized data in a 2D list format.
    """
    real_values = []
    if isinstance(values, dict):
        temp = deepcopy(values)
        for key, item in temp:
            real_values.append([key] + item)
    elif isinstance(values, list):
        real_values = deepcopy(values)
    else:
        raise ValueError("Unusable type passed for values parameter")
    maxwidth = 0
    maxheight = len(real_values)
    for item in real_values:
        if len(item) > maxwidth:
            maxwidth = len(item)
    for item in real_values:
        if len(item) < maxwidth:
            item += ["" for _ in range(maxwidth - len(item))]
    return real_values

def normalize_range(ran: list[list[int] | int] | None):
    """
    Normalizes the range to be in a format suitable for Google Sheets API (A1 format).
    :param ran: The range to be normalized. It can be in the following specific formats:
        - [[col1:int, row1:int], [col2:int, row2:int]]
        - [[col1:int, col2:int], row:int]
        - [col:int, [row1:int, row2:int]]
    :return: (str) Normalized range in a format suitable for Google Sheets API (A1 format).
    :raises ValueError: If the range is not in a valid format.
    """
    if ran is None:
        return None
    else:
        if len(ran) == 2:
            if isinstance(ran[0], list) and isinstance(ran[1], list):
                return gsutils.rowcol_to_a1(ran[0][0], ran[0][1]) + ":" + gsutils.rowcol_to_a1(ran[1][0], ran[1][1])
            elif isinstance(ran[0], list) and isinstance(ran[1], int):
                return gsutils.rowcol_to_a1(ran[0][0], ran[1]) + ":" + gsutils.rowcol_to_a1(ran[0][1], ran[1])
            elif isinstance(ran[0], int) and isinstance(ran[1], list):
                return gsutils.rowcol_to_a1(ran[0], ran[1][0]) + ":" + gsutils.rowcol_to_a1(ran[0], ran[1][1])
            else:
                raise ValueError("Invalid range format")
        else:
            raise ValueError("Invalid range format")

class GoogleSheetsStorage:
    def __init__(self, client, project_name: str, folder_id: str | None = None):
        self.client = client
        self.name = project_name
        try:
            self.file = client.open(project_name + " Storage", folder_id=folder_id)
        except gspread.SpreadsheetNotFound:
            self.file = client.create(project_name + " Storage", folder_id=folder_id)
        self.sheets = [sheet.title for sheet in self.file.worksheets]

    def write(self, sheet: str, values: dict[str, list[str | int]] | list[list[str | int]], major_dimension: str = "ROWS"):
        ind = self.sheets.index(sheet)
        worksheet = self.file.get_worksheet(ind)
        real_values = normalize_data(values)
        worksheet.update(real_values, "USER_ENTERED", major_dimension=major_dimension)

    def insert(self, sheet: str, values: dict[str, list[str | int]] | list[list[str | int]], position: str | int = "LAST", direction: str = "VERTICAL", major_dimension: str = "ROWS", input_option: str = "USER_ENTERED"):
        ind = self.sheets.index(sheet)
        worksheet = self.file.get_worksheet(ind)
        real_values = normalize_data(values)
        if position == "LAST":
            if direction == "HORIZONTAL":
                worksheet.append_cols(real_values, value_input_option=input_option, major_dimension=major_dimension)
            elif direction == "VERTICAL":
                worksheet.append_rows(real_values, value_input_option=input_option, major_dimension=major_dimension)
            else:
                raise ValueError("Direction must be 'HORIZONTAL' or 'VERTICAL'")
        elif position == "FIRST":
            if direction == "HORIZONTAL":
                worksheet.insert_cols(real_values, 1, value_input_option=input_option, major_dimension=major_dimension)
            elif direction == "VERTICAL":
                worksheet.insert_rows(real_values, 1, value_input_option=input_option, major_dimension=major_dimension)
            else:
                raise ValueError("Direction must be 'HORIZONTAL' or 'VERTICAL'")
        elif isinstance(position, int):
            if direction == "HORIZONTAL":
                worksheet.insert_cols(real_values, position, value_input_option=input_option, major_dimension=major_dimension)
            elif direction == "VERTICAL":
                worksheet.insert_rows(real_values, position, value_input_option=input_option, major_dimension=major_dimension)
            else:
                raise ValueError("Direction must be 'HORIZONTAL' or 'VERTICAL'")
        else:
            raise ValueError("Position must be 'LAST', 'FIRST' or an integer")

    def update(self, sheet: str, values: dict[str, list[str | int]] | list[list[str | int]], major_dimension: str = "ROWS", value_range: str | list[list[int] | int] | None = None, input_option: str = "USER_ENTERED"):
        ind = self.sheets.index(sheet)
        worksheet = self.file.get_worksheet(ind)
        if isinstance(value_range, list):
            value_range = normalize_range(value_range)
        real_values = normalize_data(values)
        if value_range is not None:
            worksheet.update(value_range, real_values, input_option, major_dimension=major_dimension)
        else:
            worksheet.update(real_values, input_option, major_dimension=major_dimension)

    def read(self, sheet: str, ran: str | None = None):
        ind = self.sheets.index(sheet)
        worksheet = self.file.get_worksheet(ind)
        return worksheet.get(ran)

    def create_sheet(self, name: str, vals: dict[str, list[str | int]] | list[list[str | int]] | None = None):
        self.file.add_worksheet(name, 100, 26)
        if vals is not None:
            self.write(name, vals)

    def del_sheet(self, name):
        ind = self.sheets.index(name)
        worksheet = self.file.get_worksheet(ind)
        self.file.del_worksheet(worksheet)

    def rename_sheet(self, old_name: str, new_name: str):
        ind = self.sheets.index(old_name)
        worksheet = self.file.get_worksheet(ind)
        worksheet.update_title(new_name)
        self.sheets[ind] = new_name

    def get_sheets(self):
        return self.sheets