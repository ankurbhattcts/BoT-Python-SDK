import falcon
import subprocess

from bot_python_sdk.action_service import ActionService
from bot_python_sdk.configuration_service import ConfigurationService
from bot_python_sdk.configuration_store import ConfigurationStore
from bot_python_sdk.device_status import DeviceStatus
from bot_python_sdk.logger import Logger

LOCATION = 'Controller'
INCOMING_REQUEST = 'Incoming request: '

DEVICE_ID_KEY = 'deviceId'
MAKER_ID_KEY = 'makerId'
PUBLIC_KEY_KEY = 'publicKey'

ACTION_ID = 'actionID'
VALUE_KEY = 'value'

METHOD_GET = 'GET'
METHOD_POST = 'POST'
ACTIONS_ENDPOINT = '/actions'
PAIRING_ENDPOINT = '/pairing'

""" Error Text """
ERROR_TRIGGER = 'Not allowed to trigger actions when device is not activated.'
ERROR_PAIRED = 'Device is already paired.'
ERROR_ACTION_ID = 'Missing parameter `' + ACTION_ID + '` for ' + METHOD_POST + ' ' + ACTIONS_ENDPOINT


class BaseUtilHandler:
    def __init__(self):
        self.configuration_store = ConfigurationStore()

    @staticmethod
    def call_error_logger(error, has_desc):
        Logger.error(LOCATION, error)
        if has_desc:
            raise falcon.HTTPForbidden(description=error)
        else:
            raise falcon.HTTPBadRequest

    @staticmethod
    def call_info_logger(call_type, endpoint):
        Logger.info(LOCATION, INCOMING_REQUEST + call_type + ' ' + endpoint)

    def check_device_status(self, config_status, expected_status, pair):
        if config_status is not expected_status:
            self.call_error_logger(ERROR_PAIRED, True) if pair else self.call_error_logger(ERROR_TRIGGER, True)


class ActionsResource(BaseUtilHandler):
    def __init__(self):
        self.action_service = ActionService()
        super().__init__(self)

    def on_get(self, request, response):
        self.call_info_logger(METHOD_GET, ACTIONS_ENDPOINT)
        response.media = self.action_service.get_actions()

    def on_post(self, request, response):
        configuration = self.configuration_store.get()
        self.check_device_status(configuration.get_device_status(), DeviceStatus.ACTIVE, False)
        self.call_info_logger(METHOD_POST, ACTIONS_ENDPOINT)

        data = request.media
        if ACTION_ID not in data.keys():
            self.call_error_logger(ERROR_ACTION_ID, False)

        action_id = data[ACTION_ID]
        value = data[VALUE_KEY] if VALUE_KEY in data.keys() else None
        success = self.action_service.trigger(action_id, value)
        if success:
            response.media = {'message': 'Action triggered'}
        else:
            raise falcon.HTTPServiceUnavailable


class PairingResource(BaseUtilHandler):

    def on_get(self, request, response):
        self.call_info_logger(METHOD_GET, PAIRING_ENDPOINT)
        configuration = self.configuration_store.get()
        self.check_device_status(configuration.get_device_status(), DeviceStatus.NEW, True)
        response.media = configuration.get_device_information
        subprocess.Popen(['make', 'pair'])


api = application = falcon.API()
api.add_route(ACTIONS_ENDPOINT, ActionsResource())
api.add_route(PAIRING_ENDPOINT, PairingResource())
ConfigurationService().resume_configuration()
