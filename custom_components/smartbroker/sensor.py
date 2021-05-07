from .smartbroker import Smartbroker, SecuritiesAccount, ConnectionFailed, InvalidAuth
import logging
from datetime import timedelta
from typing import Any, Dict
from homeassistant import config_entries, core
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=15)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        data = {}
        session = async_create_clientsession(hass, auto_cleanup=False)
        try:
            api = Smartbroker(session)
            await api.login(config[CONF_USERNAME], config[CONF_PASSWORD])
            account_list = await api.list_accounts()
            for account in account_list:
                if isinstance(account, SecuritiesAccount):
                    data[account.account_number] = await api.list_portfolio(
                        account.account_number
                    )
                else:
                    data[account.account_number] = account
            await api.logout()
        except InvalidAuth as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except ConnectionFailed as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        finally:
            session.detach()

        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()
    async_add_entities(
        [
            SecuritiesAccountSensor(account_number, coordinator)
            if isinstance(coordinator.data[account_number], SecuritiesAccount)
            else AccountSensor(account_number, coordinator)
            for account_number in coordinator.data
        ]
    )


class AccountSensor(CoordinatorEntity):
    def __init__(self, account_number, coordinator):
        super().__init__(coordinator)
        self.entity_id = ENTITY_ID_FORMAT.format("smartbroker_" + account_number)
        self._name = "Smartbroker Account " + account_number
        self._account_number = account_number

    def _data(self):
        return self.coordinator.data[self._account_number]

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.entity_id

    @property
    def state(self):
        return self._data().balance

    @property
    def icon(self):
        if self.unit_of_measurement == "EUR":
            return "mdi:currency-eur"
        elif self.unit_of_measurement == "USD":
            return "mdi:currency-usd"
        else:
            return "mdi:cash"

    @property
    def unit_of_measurement(self):
        return self._data().currency


class SecuritiesAccountSensor(AccountSensor):
    def __init__(self, account_number, coordinator):
        super().__init__(account_number, coordinator)
        self._name = "Smartbroker Securities Account " + account_number

    @property
    def icon(self):
        return "mdi:cash-multiple"

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return {
            **{position.name: position.value for position in self._data().positions},
            "Profit/Loss (absolute)": self._data().profit_loss_abs,
            "Profit/Loss (percent)": self._data().profit_loss_pct,
        }

