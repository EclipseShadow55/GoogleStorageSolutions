import gspread
from google.oauth2 import service_account
import json
from copy import deepcopy

# Getting config information
with open("config.json", "r") as f:
    config = json.loads(f)

# Setting up Google Sheet storage
SCOPE = ['https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(
    config["service_account_creds_filepath"], scopes=SCOPE)
gc = gspread.authorize(creds)

class GoogleSheetsStorage:
    def __init__(self, client, project_name: str, folder_id: str | None = None):
        self.client = client
        self.name = project_name
        try:
            self.file = client.open(project_name + " Storage", folder_id=folder_id)
        except gspread.SpreadSheetNotFound:
            self.file = client.create(project_name + " Storage", folder_id=folder_id)
        self.sheets = [sheet.title for sheet in self.file.worksheets]

    async def dump(self, sheet: str, values: dict[str, list[str | int]] | list[list[str | int]]):
        ind = self.sheets.index(sheet)
        worksheet = self.file.get_worksheet(ind)
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
        worksheet.update(real_values, "USER_ENTERED")

    async def load(self, sheet: str, ran: str):
        ind = self.sheets.index(sheet)
        worksheet = self.file.get_worksheet(ind)
        return worksheet.get(ran)

    async def create_sheet(self, name: str, vals: dict[str, list[str | int]] | list[list[str | int]] | None = None):
        self.file.add_worksheet(name, 100, 26)
        if vals is not None:
            await self.dump(name, vals)

    async def del_sheet(self, name):
        ind = self.sheets.index(name)
        worksheet = self.file.get_worksheet(ind)
        self.file.del_worksheet(worksheet)

    async def update(self, sheet, new_data):
        ind = self.sheets.index(sheet)
        worksheet = self.file.get_worksheet(ind)