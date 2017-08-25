import json
import os
from random import randint

import base58
import pytest
import re

from plenum.common.constants import TXN_TYPE, GET_TXN, DATA, NODE
from plenum.common.request import Request
from plenum.common.util import getTimeBasedId
from plenum.server.validator_info_tool import ValidatorNodeInfoTool
from plenum.test import waits
from plenum.test.helper import sendRandomRequests, waitForSufficientRepliesForRequests, checkSufficientRepliesReceived
# noinspection PyUnresolvedReferences
from plenum.test.pool_transactions.conftest import steward1, stewardWallet, client1Connected  # noqa
from stp_core.loop.eventually import eventually


TEST_NODE_NAME = 'Alpha'
STATUS_FILENAME = '{}_info.json'.format(TEST_NODE_NAME.lower())
PERIOD_SEC = 5
TXNS_COUNT = 8
nodeCount = 5


def test_node_status_file_schema_is_valid(status):
    assert isinstance(status, dict)
    assert 'alias' in status

    assert 'bindings' in status
    assert 'client' in status['bindings']
    assert 'ip' in status['bindings']['client']
    assert 'port' in status['bindings']['client']
    assert 'protocol' in status['bindings']['client']
    assert 'node' in status['bindings']
    assert 'ip' in status['bindings']['node']
    assert 'port' in status['bindings']['node']
    assert 'protocol' in status['bindings']['node']

    assert 'did' in status
    assert 'response-version' in status
    assert 'timestamp' in status
    assert 'verkey' in status

    assert 'metrics' in status
    assert 'average-per-second' in status['metrics']
    assert 'read-transactions' in status['metrics']['average-per-second']
    assert 'write-transactions' in status['metrics']['average-per-second']
    assert 'transaction-count' in status['metrics']
    assert 'ledger' in status['metrics']['transaction-count']
    assert 'pool' in status['metrics']['transaction-count']
    assert 'uptime' in status['metrics']

    assert 'pool' in status
    assert 'reachable' in status['pool']
    assert 'count' in status['pool']['reachable']
    assert 'list' in status['pool']['reachable']
    assert 'unreachable' in status['pool']
    assert 'count' in status['pool']['unreachable']
    assert 'list' in status['pool']['unreachable']
    assert 'total-count' in status['pool']


def test_node_status_file_alias_field_valid(status):
    assert status['alias'] == 'Alpha'


def test_node_status_file_bindings_field_valid(status, node):
    assert status['bindings']['client']['ip'] == node.clientstack.ha.host
    assert status['bindings']['client']['port'] == node.clientstack.ha.port
    assert status['bindings']['client']['protocol'] == 'tcp'
    assert status['bindings']['node']['ip'] == node.nodestack.ha.host
    assert status['bindings']['node']['port'] == node.nodestack.ha.port
    assert status['bindings']['node']['protocol'] == 'tcp'


def test_node_status_file_did_field_valid(status):
    assert status['did'] == 'JpYerf4CssDrH76z7jyQPJLnZ1vwYgvKbvcp16AB5RQ'


def test_node_status_file_response_version_field_valid(status):
    assert status['response-version'] == ValidatorNodeInfoTool.STATUS_NODE_JSON_SCHEMA_VERSION


def test_node_status_file_timestamp_field_valid(status):
    assert re.match('\d{10}', str(status['timestamp']))


def test_node_status_file_verkey_field_valid(node, status):
    assert status['verkey'] == base58.b58encode(node.nodestack.verKey)


def test_node_status_file_metrics_avg_write_field_valid(status):
    assert status['metrics']['average-per-second']['write-transactions'] == 0


def test_node_status_file_metrics_avg_read_field_valid(status):
    assert status['metrics']['average-per-second']['read-transactions'] == 0


def test_node_status_file_metrics_count_ledger_field_valid(poolTxnData, status):
    txns_num = sum(1 for item in poolTxnData["txns"] if item.get(TXN_TYPE) != NODE)
    assert status['metrics']['transaction-count']['ledger'] == txns_num


def test_node_status_file_metrics_count_pool_field_valid(status):
    assert status['metrics']['transaction-count']['pool'] == nodeCount


def test_node_status_file_metrics_uptime_field_valid(status):
    assert status['metrics']['uptime'] > 0


def test_node_status_file_pool_reachable_cnt_field_valid(status):
    assert status['pool']['reachable']['count'] == nodeCount


def test_node_status_file_pool_reachable_list_field_valid(txnPoolNodeSet, status):
    assert status['pool']['reachable']['list'] == \
        sorted(list(node.name for node in txnPoolNodeSet))


def test_node_status_file_pool_unreachable_cnt_field_valid(status):
    assert status['pool']['unreachable']['count'] == 0


def test_node_status_file_pool_unreachable_list_field_valid(status):
    assert status['pool']['unreachable']['list'] == []


def test_node_status_file_pool_total_count_field_valid(status):
    assert status['pool']['total-count'] == nodeCount


@pytest.fixture(scope='module')
def status(status_path):
    return load_status(status_path)


def load_status(path):
    with open(path) as fd:
        status = json.load(fd)
    return status


@pytest.fixture(scope='module')
def status_path(tdirWithPoolTxns, patched_dump_status_period, txnPoolNodesLooper, txnPoolNodeSet):
    txnPoolNodesLooper.runFor(PERIOD_SEC)
    path = os.path.join(tdirWithPoolTxns, STATUS_FILENAME)
    assert os.path.exists(path), '{} exists'.format(path)
    return path


@pytest.fixture(scope='module')
def patched_dump_status_period(tconf):
    old_period = tconf.DUMP_NODE_STATUS_PERIOD_SEC
    tconf.DUMP_NODE_STATUS_PERIOD_SEC = PERIOD_SEC
    yield tconf.DUMP_NODE_STATUS_PERIOD_SEC
    tconf.DUMP_NODE_STATUS_PERIOD_SEC = old_period


@pytest.fixture(scope='module')
def node(txnPoolNodeSet):
    for n in txnPoolNodeSet:
        if n.name == TEST_NODE_NAME:
            return n
    assert False, 'Pool does not have "{}" node'.format(TEST_NODE_NAME)
