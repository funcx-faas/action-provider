import logging

import globus_sdk
from globus_sdk.scopes import AuthScopes, SearchScopes
from funcx.sdk.web_client import FuncxWebClient
from funcx import FuncXClient

logger = logging.getLogger(__name__)


class FuncXLoginManager:
    """
    Implements the funcx.sdk.login_manager.protocol.LoginManagerProtocol class.
    """

    def __init__(self, authorizers: dict[str, globus_sdk.RefreshTokenAuthorizer]):
        self.authorizers = authorizers

    def get_auth_client(self) -> globus_sdk.AuthClient:
        return globus_sdk.AuthClient(
            authorizer=self.authorizers[AuthScopes.openid]
        )

    def get_search_client(self) -> globus_sdk.SearchClient:
        return globus_sdk.SearchClient(
            authorizer=self.authorizers[SearchScopes.all]
        )

    def get_funcx_web_client(self, *, base_url: str) -> FuncxWebClient:
        return FuncxWebClient(
            base_url=base_url,
            authorizer=self.authorizers[FuncXClient.FUNCX_SCOPE],
        )

    def ensure_logged_in(self):
        return True

    def logout(self):
        logger.warning("logout cannot be invoked from here!")
