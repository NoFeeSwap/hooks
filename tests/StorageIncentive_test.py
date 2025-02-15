# Copyright 2025, NoFeeSwap LLC - All rights reserved.
import pytest
import brownie
from brownie import accounts, StorageIncentiveWrapper
from Nofee import logTest, keccak256, keccakPacked

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

def test_tokenIdSlot(wrapper):
    # Check if the hash is calculated correctly.
    tx = wrapper._tokenIdSlot()
    tokenIdSlot = tx.return_value
    assert tokenIdSlot == keccak256('tokenId') - 1

@pytest.mark.parametrize('tokenId', [value0, value1, value2, value3])
@pytest.mark.parametrize('storageSlot', [storageSlot0, storageSlot1, storageSlot2, storageSlot3, storageSlot4])
def test_incrementTokenId(wrapper, tokenId, storageSlot, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the content of the tokenId slot is incremented correctly.
    tx = wrapper._incrementTokenId(tokenId, storageSlot)
    tokenIdOld, tokenIdNew = tx.return_value
    assert tokenIdOld == tokenId
    assert tokenIdNew == tokenId + 1

def test_totalEvanescentPointsOwedSlot(wrapper, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the hash is calculated correctly.
    tx = wrapper._totalEvanescentPointsOwedSlot()
    totalEvanescentPointsOwedSlot = tx.return_value
    assert totalEvanescentPointsOwedSlot == keccak256('totalEvanescentPointsOwed') - 1

@pytest.mark.parametrize('totalEvanescentPointsOwed', [value0, value1, value2, value3, value4])
@pytest.mark.parametrize('increment', [value0, value1, value2, value3, value4])
def test_updateTotalEvanescentPointsOwed(wrapper, totalEvanescentPointsOwed, increment, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the content of the totalEvanescentPointsOwed slot is updated correctly.
    if totalEvanescentPointsOwed + increment < (1 << 256):
        tx = wrapper._updateTotalEvanescentPointsOwed(totalEvanescentPointsOwed, increment)
        totalEvanescentPointsOwedIncremented = tx.return_value
        assert totalEvanescentPointsOwedIncremented == totalEvanescentPointsOwed + increment
    else:
        with brownie.reverts():
            tx = wrapper._updateTotalEvanescentPointsOwed(totalEvanescentPointsOwed, increment)

def test_poolDataSlot(wrapper, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the hash is calculated correctly.
    tx = wrapper._poolDataSlot()
    poolDataSlot = tx.return_value
    assert poolDataSlot == (keccak256('poolData') - 1) % (1 << 128)

@pytest.mark.parametrize('poolId', [value0, value1, value2, value3, value4])
def test_getPoolDataSlot(wrapper, poolId, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the poolData slot is calculated correctly.
    tx = wrapper._getPoolDataSlot(poolId)
    storageSlot = tx.return_value
    assert storageSlot == keccakPacked(['uint256', 'uint128'], [poolId, (keccak256('poolData') - 1) % (1 << 128)])

@pytest.mark.parametrize('value', [value0, value1, value2, value3, value4])
def test_readPoolData(wrapper, value, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the content of poolData slot is decoded correctly.
    tx = wrapper._readPoolData(value)
    blockNumber, qLower, qUpper, activeEvanescentPointsPerShare = tx.return_value
    assert blockNumber == value >> 224
    assert qLower == (value >> 160) % (1 << 64)
    assert qUpper == (value >> 96) % (1 << 64)
    assert activeEvanescentPointsPerShare == value % (1 << 96)

def test_incentiveDataSlot(wrapper, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the hash is calculated correctly.
    tx = wrapper._incentiveDataSlot()
    incentiveDataSlot = tx.return_value
    assert incentiveDataSlot == (keccak256('incentiveData') - 1) % (1 << 128)

@pytest.mark.parametrize('tokenId', [value0, value1, value2, value3, value4])
def test_getIncentiveDataSlot(wrapper, tokenId, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the incentiveData slot is calculated correctly.
    tx = wrapper._getIncentiveDataSlot(tokenId)
    storageSlot = tx.return_value
    assert storageSlot == keccakPacked(['uint256', 'uint128'], [tokenId, (keccak256('incentiveData') - 1) % (1 << 128)])

def test_evanescentPointsPerShareMappingSlot(wrapper, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the hash is calculated correctly.
    tx = wrapper._evanescentPointsPerShareMappingSlot()
    evanescentPointsPerShareMappingSlot = tx.return_value
    assert evanescentPointsPerShareMappingSlot == (keccak256('evanescentPointsPerShareMapping') - 1) % (1 << 64)

@pytest.mark.parametrize('poolId', [value0, value1, value2, value3, value4])
@pytest.mark.parametrize('logPrice', [logPrice0, logPrice1, logPrice2, logPrice3, logPrice4])
def test_getEvanescentPointsPerShareMappingSlot(wrapper, poolId, logPrice, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the evanescentPointsPerShareMapping slots are calculated correctly.
    tx = wrapper._getEvanescentPointsPerShareMappingSlot(poolId, logPrice)
    evanescentPointsPerShareMappingSlot = tx.return_value
    assert evanescentPointsPerShareMappingSlot == keccakPacked(['uint256', 'uint64', 'uint64'], [poolId, logPrice, (keccak256('evanescentPointsPerShareMapping') - 1) % (1 << 64)])