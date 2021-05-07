"""Config flow for Smartbroker integration."""
import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from .smartbroker import Smartbroker, InvalidAuth, ConnectionFailed

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smartbroker."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                async with aiohttp.ClientSession() as session:
                    sb = Smartbroker(session)
                    await sb.login(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                    await sb.logout()

                return self.async_create_entry(title="Smartbroker", data=user_input)
            except ConnectionFailed:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
