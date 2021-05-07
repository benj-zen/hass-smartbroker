from bs4 import BeautifulSoup
from dataclasses import dataclass

from typing import List

BASE_URL = "https://b2b.dab-bank.de/"
LOGIN_START_ENDPOINT = "smartbroker/"
LOGIN_ENDPOINT = "smartbroker/b3SecurityLoginCheck.xhtml"
LOGOUT_ENDPOINT = "smartbroker/Logout.xhtml"
LIST_ACCOUNTS_ENDPOINT = "smartbroker/Finanzuebersicht/"
LIST_PORTFOLIO_ENDPOINT = "Tradingcenter/Depot/Depotuebersicht/"


@dataclass
class Account:
    account_number: str
    currency: str
    balance: float


@dataclass
class Position:
    name: str
    wkn: str
    amount: float
    buy_quote: float
    buy_quote_currency: str
    buy_value: float
    buy_date: str
    quote: float
    quote_currency: str
    value: float
    profit_loss_abs: float
    profit_loss_pct: float


@dataclass
class SecuritiesAccount(Account):
    profit_loss_abs: float
    profit_loss_pct: float
    positions: List[Position]


def parse_float(text: str):
    return float(text.strip().replace(".", "").replace(",", ".").replace("+", ""))


class InvalidAuth(Exception):
    pass


class ConnectionFailed(Exception):
    pass


class Smartbroker:
    def __init__(self, session):
        self.session = session

    async def login(self, access_number: str, identifier: str):
        try:
            r = await self.session.get(BASE_URL + LOGIN_START_ENDPOINT)
            if r.status >= 400:
                raise ConnectionFailed()
            r = await self.session.post(
                BASE_URL + LOGIN_ENDPOINT,
                data={
                    "login_query_string": "",
                    "campaignIDs_MINIAPP_login": "",
                    "accessNumber": access_number,
                    "identifier": identifier,
                },
            )
            if r.status >= 400:
                raise ConnectionFailed()
        except Exception:
            raise ConnectionFailed()
        text = await r.text()
        if text.find("Ihre Legitimation war nicht erfolgreich") != -1:
            raise InvalidAuth()

    async def logout(self):
        try:
            r = await self.session.get(BASE_URL + LOGOUT_ENDPOINT)
            if r.status >= 400:
                raise ConnectionFailed()
        except Exception:
            raise ConnectionFailed()

    async def list_accounts(self) -> List[Account]:
        try:
            r = await self.session.get(BASE_URL + LIST_ACCOUNTS_ENDPOINT)
        except Exception:
            raise ConnectionFailed()
        if r.status >= 400:
            raise ConnectionFailed()
        html = BeautifulSoup(await r.text(), "html.parser")
        table_rows = html.find("table", {"id": "accountSectionTable"}).find_all("tr")
        assert len(table_rows) > 1 and len(table_rows[0].find_all("th")) == 7
        table_rows = table_rows[1:]
        accounts = []
        for row in table_rows:
            account_number = row.attrs["id"]
            currency = row.find("span", {"id": "currencySpan"}).text
            balance = parse_float(row.find("span", {"id": "amountSpan"}).text)
            profit_loss_span = row.find("span", {"id": "winLossSpan"})
            profit_loss = (
                parse_float(profit_loss_span.text.replace("%", ""))
                if profit_loss_span is not None
                else 0
            )

            account_type = row.find_all("td")[2].text
            if account_type.startswith("Depot"):
                profit_loss_abs = round(profit_loss * balance / (profit_loss + 100), 2)
                accounts.append(
                    SecuritiesAccount(
                        account_number,
                        currency,
                        balance,
                        profit_loss_abs,
                        profit_loss,
                        [],
                    )
                )
            elif account_type.startswith("Verrechnungskonto"):
                accounts.append(Account(account_number, currency, balance,))
        return accounts

    async def list_portfolio(self, account_number: str) -> SecuritiesAccount:
        try:
            r = await self.session.get(
                BASE_URL + LIST_PORTFOLIO_ENDPOINT,
                params={"securityAccountNumber": account_number},
            )
        except Exception:
            raise ConnectionFailed()
        if r.status >= 400:
            raise ConnectionFailed()
        html = BeautifulSoup(await r.text(), "html.parser")
        table_rows = html.find("table", {"id": "depotOverviewTable"}).find_all("tr")
        summary_row = table_rows[-1]
        table_rows = table_rows[1:-1]
        positions = []
        for row in table_rows:
            cells = row.find_all("td")
            name = cells[0].find("a").text.strip()
            wkn = cells[0].find_all("div", {"class": "bez"})[0].text
            amount = parse_float(
                cells[0].find_all("div", {"class": "bez"})[1].text.replace("Stück", "")
            )
            if int(amount) == amount:
                amount = int(amount)
            buy_info_spans = cells[1].find_all("span")
            buy_quote = parse_float(buy_info_spans[3].text)
            buy_quote_currency = buy_info_spans[0].text
            buy_value = parse_float(buy_info_spans[4].text)
            buy_date = buy_info_spans[1].text

            quote_info_spans = cells[2].find_all("span")
            quote_currency = quote_info_spans[0].text
            quote = parse_float(quote_info_spans[1].find("strong").text)

            value_info_spans = cells[3].find_all("span")
            value = parse_float(value_info_spans[0].find("strong").text)
            profit_loss_abs = parse_float(value_info_spans[2].text)
            profit_loss_pct = parse_float(value_info_spans[5].text.replace("%", ""))
            positions.append(
                Position(
                    name,
                    wkn,
                    amount,
                    buy_quote,
                    buy_quote_currency,
                    buy_value,
                    buy_date,
                    quote,
                    quote_currency,
                    value,
                    profit_loss_abs,
                    profit_loss_pct,
                )
            )
        summary_spans = summary_row.find_all("span")
        balance = parse_float(summary_spans[0].text.replace("EUR", ""))
        profit_loss_abs = parse_float(summary_spans[1].text.replace("EUR", ""))
        profit_loss_pct = parse_float(summary_spans[2].text.replace("%", ""))

        return SecuritiesAccount(
            account_number, "EUR", balance, profit_loss_abs, profit_loss_pct, positions
        )
