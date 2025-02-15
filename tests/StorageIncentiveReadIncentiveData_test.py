# Copyright 2025, NoFeeSwap LLC - All rights reserved.
import pytest
from brownie import accounts, StorageIncentiveWrapper
from Nofee import logTest, toInt

value0 = 0x0000000000000000000000000000000000000000000000000000000000000000
value1 = 0x0000000000000000000000000000000000000000000000000000000000000001
value2 = 0xF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00F
value3 = 0x8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
value4 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

balance0 = 0x00000000000000000000000000000000
balance1 = 0x00000000000000000000000000000001
balance2 = 0xF00FF00FF00FF00FF00FF00FF00FF00F
balance3 = 0x8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
balance4 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
balance5 = 0 - 0x00000000000000000000000000000001
balance6 = 0 - 0xF00FF00FF00FF00FF00FF00FF00FF00F
balance7 = 0 - 0x8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
balance8 = 0 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

storageSlot0 = 0x0000000000000000000000000000000000000000000000000000000000000000
storageSlot1 = 0x0000000000000000000000000000000000000000000000000000000000000001
storageSlot2 = 0xF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00F
storageSlot3 = 0x8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
storageSlot4 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

logPrice0 = 0x0000000000000000
logPrice1 = 0x0000000000000001
logPrice2 = 0xF00FF00FF00FF00F
logPrice3 = 0x8FFFFFFFFFFFFFFF
logPrice4 = 0xFFFFFFFFFFFFFFFF

block0 = 0x00000000
block1 = 0x40000000
block2 = 0x80000000
block3 = 0xFFFFFFFF

points0 = 0x000000000000000000000000
points1 = 0x000000000000000000000001
points2 = 0xF00FF00FF00FF00FF00FF00F
points3 = 0x8FFFFFFFFFFFFFFFFFFFFFFF
points4 = 0xFFFFFFFFFFFFFFFFFFFFFFFF

@pytest.fixture(autouse=True)
def wrapper(fn_isolation):
    return StorageIncentiveWrapper.deploy({'from': accounts[0]})

@pytest.mark.parametrize('storageSlot', [storageSlot0, storageSlot2, storageSlot4])
@pytest.mark.parametrize('content0', [value0, value2, value4])
@pytest.mark.parametrize('content1', [value0, value2, value4])
@pytest.mark.parametrize('content2', [value0, value2, value4])
def test_readIncentiveData(wrapper, storageSlot, content0, content1, content2, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the content of incentiveData slot is decoded correctly.
    tx = wrapper._readIncentiveData(storageSlot, content0, content1, content2)
    poolId, qMin, qMax, shares, evanescentPointsPerShareSubtrahend, evanescentPointsOwed = tx.return_value
    assert poolId == ((content0 >> 160) << 160) + toInt(wrapper.address)
    assert evanescentPointsPerShareSubtrahend == content0 % (1 << 96)
    assert qMin == (content1 >> 192)
    assert qMax == (content1 >> 128) % (1 << 64)
    assert shares == content1 % (1 << 128)
    assert evanescentPointsOwed == content2