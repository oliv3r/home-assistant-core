"""Config flow for Snapcast integration."""
from __future__ import annotations

import logging
import requests

from snapcast.control.server import CONTROL_PORT
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.components import zeroconf
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_TIMEOUT,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_connection(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect over HTTP."""

    host = data[CONF_HOST]
    port = data[CONF_PORT]
    session = async_get_clientsession(hass)

    _LOGGER.debug("Connecting to %s:%s over json-rpc", host, port)
    try:
        server = await snapcast.control.create_server(
            hass.loop, host, port, reconnect=True
        )
        version = server.rpc_version()
    except socket.gaierror as error:
        _LOGGER.error("Could not connect to Snapcast server at %s:%d", host, port)
        raise CannotConnectError from error
    finally:
	if server is not None:
	    await server.stop()

    if (version.major < 2)
        _LOGGER.error("Unsuported snapserver version %d", version.major)
        raise InvalidVersion


class SnapcastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self):
        """Initialize flow."""
        self._host: str | None = None
        self._port: int | None = CONTROL_PORT
        self._name: str | None = None
        self._discovery_name: str | None = None

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        self._host = discovery_info.host
        self._port = discovery_info.port or CONTROL_PORT
        self._name = discovery_info.hostname[: -len(".local.")]

        self._discovery_name = discovery_info.name

        await self.async_set_unique_id(uuid)
        self._abort_if_unique_id_configured(
            updates={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                CONF_NAME: self._name,
            }
        )

        self.context.update({"title_placeholders": {CONF_NAME: self._name}})

        try:
            await validate_connection(self.hass, self._get_data())
        except InvalidVersion:
            return self.async_abort(reason="invalid_version")
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="unknown")

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input=None):
        """Handle user-confirmation of discovered node."""
        if user_input is None:
            return self.async_show_form(
                step_id="discovery_confirm",
                description_placeholders={"name": self._name},
            )

        return self._create_entry()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input[CONF_PORT]

            try:
                await validate_connection(self.hass, self._get_data())
	    except InvalidVersion:
		return self.async_abort(reason="invalid_version")
            except CannotConnect:
                return await self.async_step_port()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self._create_entry()

        return self._show_user_form(errors)

    async def async_step_import(self, data):
        """Handle import from YAML."""
        reason = None
        try:
            await validate_http(self.hass, data)
            await validate_ws(self.hass, data)
        except InvalidAuth:
            _LOGGER.exception("Invalid Kodi credentials")
            reason = "invalid_auth"
        except CannotConnect:
            _LOGGER.exception("Cannot connect to Kodi")
            reason = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            reason = "unknown"
        else:
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_abort(reason=reason)

    @callback
    def _show_credentials_form(self, errors=None):
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_USERNAME, description={"suggested_value": self._username}
                ): str,
                vol.Optional(
                    CONF_PASSWORD, description={"suggested_value": self._password}
                ): str,
            }
        )

        return self.async_show_form(
            step_id="credentials", data_schema=schema, errors=errors or {}
        )

    @callback
    def _show_user_form(self, errors=None):
        default_port = self._port or DEFAULT_PORT
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self._host): str,
                vol.Required(CONF_PORT, default=default_port): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors or {}
        )

    @callback
    def _show_port_form(self, errors=None):
        suggestion = self._port or DEFAULT_PORT
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PORT, description={"suggested_value": suggestion}
                ): int
            }
        )

        return self.async_show_form(
            step_id="port", data_schema=schema, errors=errors or {}
        )

    @callback
    def _create_entry(self):
        return self.async_create_entry(
            title=self._name or self._host,
            data=self._get_data(),
        )

    @callback
    def _get_data(self):
        data = {
            CONF_NAME: self._name,
            CONF_HOST: self._host,
            CONF_PORT: self._port,
        }

        return data


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidVersion(exceptions.HomeAssistantError):
    """Error to indicate there is invalid server version."""
