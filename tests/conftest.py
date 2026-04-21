import pytest

from opentdx.client.exQuotationClient import exQuotationClient
from opentdx.client.macQuotationClient import macQuotationClient,macExQuotationClient
from opentdx.client.quotationClient import QuotationClient
from opentdx.tdxClient import TdxClient


@pytest.fixture(scope="session")
def tdx():
    client = TdxClient()
    client.quotation_client = QuotationClient(True, True)
    client.ex_quotation_client = exQuotationClient(True, True)
    client.quotation_client.connect().login()
    client.ex_quotation_client.connect().login()
    yield client
    if client.quotation_client.connected:
        client.quotation_client.disconnect()
    if client.ex_quotation_client.connected:
        client.ex_quotation_client.disconnect()


@pytest.fixture(scope="session")
def qc():
    client = QuotationClient(True, True)
    client.connect().login()
    yield client
    client.disconnect()


@pytest.fixture(scope="session")
def eqc():
    client = exQuotationClient(True, True)
    client.connect().login()
    yield client
    client.disconnect()


@pytest.fixture(scope="session")
def mqc():
    client = macQuotationClient(True, True)
    client.connect()
    yield client
    client.disconnect()
    
@pytest.fixture(scope="session")
def meqc():
    client = macExQuotationClient(True, True)
    client.connect()
    yield client
    client.disconnect()

@pytest.fixture(scope="session")
def sp_qc():
    client = QuotationClient(True, True)
    client.sp().connect().login()
    yield client
    client.disconnect()
