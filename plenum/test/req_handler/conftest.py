import pytest

from state.pruning_state import PruningState
from storage.kv_in_memory import KeyValueStorageInMemory

from common.serializers.serialization import config_state_serializer
from plenum.common.util import randomString
from plenum.server.request_handlers.utils import encode_state_value

from plenum.common.constants import TRUSTEE, TXN_TYPE, TXN_AUTHOR_AGREEMENT, TXN_AUTHOR_AGREEMENT_TEXT, \
    TXN_AUTHOR_AGREEMENT_VERSION, DOMAIN_LEDGER_ID, TXN_AUTHOR_AGREEMENT_RETIREMENT_TS
from plenum.common.request import Request
from plenum.server.database_manager import DatabaseManager
from plenum.server.request_handlers.static_taa_helper import StaticTAAHelper
from plenum.server.request_handlers.txn_author_agreement_handler import TxnAuthorAgreementHandler

from plenum.test.req_handler.helper import update_nym
from plenum.test.testing_utils import FakeSomething
from state.state import State


@pytest.fixture(scope="function")
def domain_state(tconf):
    state = State()
    state.txn_list = {}
    state.get = lambda key, isCommitted=False: state.txn_list.get(key, None)
    state.set = lambda key, value, isCommitted=False: state.txn_list.update({key: value})
    return state


@pytest.fixture(scope="function")
def taa_request(tconf, domain_state):
    identifier = "identifier"
    update_nym(domain_state, identifier, TRUSTEE)
    operation = {TXN_TYPE: TXN_AUTHOR_AGREEMENT,
                 TXN_AUTHOR_AGREEMENT_TEXT: "text",
                 TXN_AUTHOR_AGREEMENT_VERSION: "version{}".format(randomString(5))}
    return Request(identifier=identifier,
                   signature="sign",
                   operation=operation)


@pytest.fixture(scope="function")
def config_state():
    return PruningState(KeyValueStorageInMemory())


@pytest.fixture(scope="function")
def txn_author_agreement_handler(tconf, domain_state, config_state):
    data_manager = DatabaseManager()
    handler = TxnAuthorAgreementHandler(data_manager)
    data_manager.register_new_database(handler.ledger_id,
                                       FakeSomething(),
                                       config_state)
    data_manager.register_new_database(DOMAIN_LEDGER_ID,
                                       FakeSomething(),
                                       domain_state)
    return handler

