# Copyright 2025, NoFeeSwap LLC - All rights reserved.
import pytest
import brownie
from brownie import web3, accounts, AccessIncentive, Nofeeswap, NofeeswapDelegatee, ERC20FixedSupply, Deployer, Incentive, Operator, IncentiveDeployer, IncentiveWrapper
from sympy import sqrt, Integer, floor
from Nofee import logTest, PUSH32, MODIFY_POSITION, REVERT, address0, swapSequence, mintIncentiveSequence, burnIncentiveSequence, keccak, toInt, twosComplementInt8, encodeKernelCompact, encodeCurve, getPoolId
from eth_abi import encode
from eth_abi.packed import encode_packed
from sha3 import keccak_256

@pytest.fixture(autouse=True)
def deployment(fn_isolation):
    root = accounts[0]
    owner = accounts[1]
    other = accounts[2]
    deployer = Deployer.deploy(root, {'from': root})
    delegatee = deployer.addressOf(1)
    nofeeswap = deployer.addressOf(2)
    deployer.create3(
        1,
        NofeeswapDelegatee.bytecode + encode(
            ['address'],
            [nofeeswap]
        ).hex(), 
        {'from': root}
    )
    deployer.create3(
        2,
        Nofeeswap.bytecode + encode(
            ['address', 'address'],
            [delegatee, root.address]
        ).hex(), 
        {'from': root}
    )
    delegatee = NofeeswapDelegatee.at(delegatee)
    nofeeswap = Nofeeswap.at(nofeeswap)
    operator = Operator.deploy(nofeeswap, address0, address0, address0, {'from': root})
    access = AccessIncentive.deploy({'from': root})

    nofeeswap.dispatch(delegatee.modifyProtocol.encode_input(
        (123 << 208) + (456 << 160) + int(root.address, 16)
    ), {'from': root})

    return root, owner, other, nofeeswap, delegatee, access, deployer, operator

def test_deployIncentive(chain, deployment, request, worker_id):
    logTest(request, worker_id)
    
    root, owner, other, nofeeswap, delegatee, access, deployer, operator = deployment

    token0 = ERC20FixedSupply.deploy("ERC20_0", "ERC20_0", 2**120, owner, {'from': owner})
    token1 = ERC20FixedSupply.deploy("ERC20_1", "ERC20_1", 2**120, owner, {'from': owner})
    if toInt(token0.address) > toInt(token1.address):
        token0, token1 = token1, token0
    tag0 = toInt(token0.address)
    tag1 = toInt(token1.address)

    rewardToken = ERC20FixedSupply.deploy("REWARD", "REWARD", 2**120, root, {'from': root})

    startBlock = chain[-1].number + 50
    endBlock = chain[-1].number + 250

    incentiveDeployer = IncentiveDeployer.deploy({'from': root})

    with brownie.reverts('TagsOutOfOrder: ' + str(tag1) + ', ' + str(tag0)):
        incentiveDeployer.deploy(
            Incentive.bytecode + encode(
                ['address', 'address', 'address', 'address', 'address', 'uint256', 'uint256', 'address', 'address', 'uint32', 'uint32'],
                [nofeeswap.address, address0, address0, address0, root.address, tag1, tag0, other.address, rewardToken.address, startBlock, endBlock]
            ).hex(),
            {'from': root}
        )

    with brownie.reverts('InvalidStartBlock: ' + str(chain[-1].number - 10) + ', ' + str(chain[-1].number + 1)):
        incentiveDeployer.deploy(
            Incentive.bytecode + encode(
                ['address', 'address', 'address', 'address', 'address', 'uint256', 'uint256', 'address', 'address', 'uint32', 'uint32'],
                [nofeeswap.address, address0, address0, address0, root.address, tag0, tag1, other.address, rewardToken.address, chain[-1].number - 10, endBlock]
            ).hex(),
            {'from': root}
        )

    with brownie.reverts('InvalidEndBlock: ' + str(startBlock) + ', ' + str(startBlock)):
        incentiveDeployer.deploy(
            Incentive.bytecode + encode(
                ['address', 'address', 'address', 'address', 'address', 'uint256', 'uint256', 'address', 'address', 'uint32', 'uint32'],
                [nofeeswap.address, address0, address0, address0, root.address, tag0, tag1, other.address, rewardToken.address, startBlock, startBlock]
            ).hex(),
            {'from': root}
        )

    incentive = Incentive.deploy(
        nofeeswap.address,
        address0,
        address0,
        address0,
        root.address,
        tag0,
        tag1,
        other.address,
        rewardToken.address,
        startBlock,
        endBlock,
        {'from': root}
    )

    assert incentive.incentivePoolFactory() == root.address
    assert incentive.tag0() == tag0
    assert incentive.tag1() == tag1
    assert incentive.payMaster() == other.address
    assert incentive.rewardToken() == rewardToken.address
    assert incentive.startBlock() == startBlock
    assert incentive.endBlock() == endBlock
    assert access._readIncentiveTokenId(incentive) == 1

def test_initialize(chain, deployment, request, worker_id):
    logTest(request, worker_id)
    
    root, owner, other, nofeeswap, delegatee, access, deployer, operator = deployment

    token0 = ERC20FixedSupply.deploy("ERC20_0", "ERC20_0", 2**120, owner, {'from': owner})
    token1 = ERC20FixedSupply.deploy("ERC20_1", "ERC20_1", 2**120, owner, {'from': owner})
    if toInt(token0.address) > toInt(token1.address):
        token0, token1 = token1, token0
    rewardToken = ERC20FixedSupply.deploy("REWARD", "REWARD", 2**120, root, {'from': root})
    tag0 = toInt(token0.address)
    tag1 = toInt(token1.address)

    startBlock = chain[-1].number + 50
    endBlock = chain[-1].number + 250

    incentiveDeploymentSalt = 11
    incentive = deployer.addressOf(incentiveDeploymentSalt)
    deployer.create3(
        incentiveDeploymentSalt,
        Incentive.bytecode + encode(
            ['address', 'address', 'address', 'address', 'address', 'uint256', 'uint256', 'address', 'address', 'uint32', 'uint32'],
            [nofeeswap.address, address0, address0, address0, root.address, toInt(token0.address), toInt(token1.address), incentive, rewardToken.address, startBlock, endBlock]
        ).hex(),
        {'from': root}
    )
    incentive = Incentive.at(incentive)

    kernel = [
      [0, 0],
      [2 ** 40, 2 ** 15]
    ]
    curve = [2 ** 40 + 1, 2 ** 40 + 1 + 2 ** 40]
    lower = min(curve[0], curve[1])
    upper = max(curve[0], curve[1])

    logOffset = -5

    with brownie.reverts('OnlyByNofeeswap: ' + root.address.lower()):
        tx = incentive.preInitialize("", {'from': root})

    with brownie.reverts('OnlyByNofeeswap: ' + root.address.lower()):
        tx = incentive.midMint("", {'from': root})

    with brownie.reverts('OnlyByNofeeswap: ' + root.address.lower()):
        tx = incentive.midBurn("", {'from': root})

    with brownie.reverts('OnlyByNofeeswap: ' + root.address.lower()):
        tx = incentive.midSwap("", {'from': root})

    with brownie.reverts('OnlyByNofeeswap: ' + root.address.lower()):
        tx = incentive.midDonate("", {'from': root})

    with brownie.reverts('IncompatibleFlags: '):
        tx = nofeeswap.dispatch(
          delegatee.initialize.encode_input(
              (0 << 188) + (twosComplementInt8(logOffset) << 180) + (0b00000000001001001001 << 160) + toInt(incentive.address),
              tag0,
              tag1,
              0x800000000000,
              encodeKernelCompact(kernel),
              encodeCurve(curve),
              b"HookData"
          ),
          {'from': root}
        )

    unsaltedPoolId = (0 << 188) + (twosComplementInt8(logOffset) << 180) + (0b01000000001001001001 << 160) + toInt(incentive.address)
    poolId = getPoolId(root.address, unsaltedPoolId)

    with brownie.reverts('InvalidTag0: ' + str(tag0 + 1)):
        tx = nofeeswap.dispatch(
          delegatee.initialize.encode_input(
              unsaltedPoolId,
              tag0 + 1,
              tag1,
              0x800000000000,
              encodeKernelCompact(kernel),
              encodeCurve(curve),
              b"HookData"
          ),
          {'from': root}
        )

    with brownie.reverts('InvalidTag1: ' + str(tag1 + 1)):
        tx = nofeeswap.dispatch(
          delegatee.initialize.encode_input(
              unsaltedPoolId,
              tag0,
              tag1 + 1,
              0x800000000000,
              encodeKernelCompact(kernel),
              encodeCurve(curve),
              b"HookData"
          ),
          {'from': root}
        )

    with brownie.reverts('InvalidFactory: ' + owner.address.lower()):
        tx = nofeeswap.dispatch(
          delegatee.initialize.encode_input(
              unsaltedPoolId,
              tag0,
              tag1,
              0x800000000000,
              encodeKernelCompact(kernel),
              encodeCurve(curve),
              b"HookData"
          ),
          {'from': owner}
        )

    tx = nofeeswap.dispatch(
      delegatee.initialize.encode_input(
          unsaltedPoolId,
          tag0,
          tag1,
          0x800000000000,
          encodeKernelCompact(kernel),
          encodeCurve(curve),
          b"HookData"
      ),
      {'from': root}
    )

    _blockNumber, _lower, _upper, _activeRewardPerShare = access._readPoolData(incentive, poolId)
    assert _lower == lower
    assert _upper == upper
    assert _activeRewardPerShare == 0

def test_modifyPosition(chain, deployment, request, worker_id):
    logTest(request, worker_id)
    
    root, owner, other, nofeeswap, delegatee, access, deployer, operator = deployment

    token0 = ERC20FixedSupply.deploy("ERC20_0", "ERC20_0", 2**120, owner, {'from': owner})
    token1 = ERC20FixedSupply.deploy("ERC20_1", "ERC20_1", 2**120, owner, {'from': owner})
    token0.approve(operator, 2 ** 120, {'from': owner})
    token1.approve(operator, 2 ** 120, {'from': owner})
    token0.transfer(root, 2 ** 119, {'from': owner})
    token1.transfer(root, 2 ** 119, {'from': owner})
    token0.approve(operator, 2 ** 120, {'from': root})
    token1.approve(operator, 2 ** 120, {'from': root})
    nofeeswap.setOperator(operator, True, {'from': owner})
    if toInt(token0.address) > toInt(token1.address):
        token0, token1 = token1, token0
    rewardToken = ERC20FixedSupply.deploy("REWARD", "REWARD", 2**120, root, {'from': root})
    tag0 = toInt(token0.address)
    tag1 = toInt(token1.address)

    startBlock = chain[-1].number + 50
    endBlock = chain[-1].number + 250

    incentiveDeploymentSalt = 12
    incentive = deployer.addressOf(incentiveDeploymentSalt)
    deployer.create3(
        incentiveDeploymentSalt,
        Incentive.bytecode + encode(
            ['address', 'address', 'address', 'address', 'address', 'uint256', 'uint256', 'address', 'address', 'uint32', 'uint32'],
            [nofeeswap.address, address0, address0, address0, root.address, toInt(token0.address), toInt(token1.address), incentive, rewardToken.address, startBlock, endBlock]
        ).hex(), 
        {'from': root}
    )
    incentive = Incentive.at(incentive)

    kernel = [
      [0, 0],
      [2 ** 40, 2 ** 15]
    ]
    curve = [2 ** 50 + 1, 2 ** 50 + 1 + 2 ** 40]
    lower = min(curve[0], curve[1])
    upper = max(curve[0], curve[1])

    logOffset = -5
    unsaltedPoolId = (1 << 188) + (twosComplementInt8(logOffset) << 180) + (0b01000000001001001001 << 160) + toInt(incentive.address)
    poolId = getPoolId(root.address, unsaltedPoolId)

    tx = nofeeswap.dispatch(
      delegatee.initialize.encode_input(
          unsaltedPoolId,
          tag0,
          tag1,
          0x800000000000,
          encodeKernelCompact(kernel),
          encodeCurve(curve),
          b"HookData"
      ),
      {'from': root}
    )

    unsaltedPoolIdInvalid = (2 << 188) + (twosComplementInt8(logOffset) << 180) + (0b01000000001001001001 << 160) + toInt(incentive.address)
    poolIdInvalid = getPoolId(root.address, unsaltedPoolIdInvalid)

    tx = nofeeswap.dispatch(
      delegatee.initialize.encode_input(
          unsaltedPoolIdInvalid,
          tag0,
          tag1,
          0x800000000000,
          encodeKernelCompact(kernel),
          encodeCurve(curve),
          b"HookData"
      ),
      {'from': root}
    )

    deadline = 2 ** 32 - 1
    hookData = encode(['uint256', 'address'], [0, owner.address])

    qMin = lower - (1 << 63) + (logOffset * (1 << 59))
    qMax = upper - (1 << 63) + (logOffset * (1 << 59))
    shares = 1000000
    tagShares = keccak(['uint256', 'int256', 'int256'], [poolId, qMin, qMax])

    data = mintIncentiveSequence(nofeeswap, incentive, token0, token1, tagShares, poolId, qMin, qMax, shares, hookData, deadline)
    tx = nofeeswap.unlock(operator, data, {'from': owner})

    _poolId, _qMin, _qMax, _shares, _evanescentPointsPerShareSubtrahend, _evanescentPointsOwed = access._readIncentiveData(incentive, 1)

    assert _poolId == poolId
    assert _qMin == lower
    assert _qMax == upper
    assert _shares == shares
    assert _evanescentPointsPerShareSubtrahend == 0
    assert _evanescentPointsOwed == 0

    ###########################

    hookData = encode(['uint256', 'address'], [1, owner.address])

    data = mintIncentiveSequence(nofeeswap, incentive, token0, token1, tagShares, poolId, qMin, qMax, shares, hookData, deadline)
    tx = nofeeswap.unlock(operator, data, {'from': root})

    _poolId, _logPriceMinOffsetted, _logPriceMaxOffsetted, _shares, _evanescentPointsPerShareSubtrahend, _evanescentPointsOwed = access._readIncentiveData(incentive, 1)

    assert _poolId == poolId
    assert _logPriceMinOffsetted == lower
    assert _logPriceMaxOffsetted == upper
    assert _shares == 2 * shares
    assert _evanescentPointsPerShareSubtrahend == 0
    assert _evanescentPointsOwed == 0

    ###########################

    sequence = [0] * 3
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, shares, 1]
    )
    sequence[1] = encode_packed(
      ['uint8', 'uint256', 'uint64', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [MODIFY_POSITION, poolIdInvalid, lower, upper, 1, 0, 0, 0, len(hookData), hookData]
    )
    sequence[2] = encode_packed(
      ['uint8'],
      [REVERT]
    )
    data = encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence)
    with brownie.reverts('InvalidPoolId: ' + str(poolId) + ', ' + str(poolIdInvalid)):
        tx = nofeeswap.unlock(operator, data, {'from': root})
    
    ###########################

    sequence = [0] * 3
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, shares, 1]
    )
    sequence[1] = encode_packed(
      ['uint8', 'uint256', 'uint64', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [MODIFY_POSITION, poolId, lower - upper + lower, upper, 1, 0, 0, 0, len(hookData), hookData]
    )
    sequence[2] = encode_packed(
      ['uint8'],
      [REVERT]
    )
    data = encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence)
    with brownie.reverts('InvalidLogPriceMin: ' + str(lower) + ', ' + str(lower - upper + lower)):
        tx = nofeeswap.unlock(operator, data, {'from': root})

    ###########################

    sequence = [0] * 3
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, shares, 1]
    )
    sequence[1] = encode_packed(
      ['uint8', 'uint256', 'uint64', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [MODIFY_POSITION, poolId, lower, upper + upper - lower, 1, 0, 0, 0, len(hookData), hookData]
    )
    sequence[2] = encode_packed(
      ['uint8'],
      [REVERT]
    )
    data = encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence)
    with brownie.reverts('InvalidLogPriceMax: ' + str(upper) + ', ' + str(upper + upper - lower)):
        tx = nofeeswap.unlock(operator, data, {'from': root})

    ###########################

    data = burnIncentiveSequence(token0, token1, owner, operator, tagShares, poolId, qMin, qMax, 2 * shares, hookData, deadline)
    with brownie.reverts('OutstandingAmount: '):
        tx = nofeeswap.unlock(operator, data, {'from': root})

    ###########################

    data = burnIncentiveSequence(token0, token1, owner, operator, tagShares, poolId, qMin, qMax, 2 * shares, hookData, deadline)
    tx = nofeeswap.unlock(operator, data, {'from': owner})

    _poolId, _logPriceMinOffsetted, _logPriceMaxOffsetted, _shares, _evanescentPointsPerShareSubtrahend, _evanescentPointsOwed = access._readIncentiveData(incentive, 1)

    assert _poolId == poolId
    assert _logPriceMinOffsetted == lower
    assert _logPriceMaxOffsetted == upper
    assert _shares == 0
    assert _evanescentPointsPerShareSubtrahend == 0
    assert _evanescentPointsOwed == 0

def test_modifyPositionWithIncentiveAsOperator(chain, deployment, request, worker_id):
    logTest(request, worker_id)
    
    root, owner, other, nofeeswap, delegatee, access, deployer, operator = deployment

    token0 = ERC20FixedSupply.deploy("ERC20_0", "ERC20_0", 2**120, owner, {'from': owner})
    token1 = ERC20FixedSupply.deploy("ERC20_1", "ERC20_1", 2**120, owner, {'from': owner})
    token0.transfer(root, 2 ** 119, {'from': owner})
    token1.transfer(root, 2 ** 119, {'from': owner})
    if toInt(token0.address) > toInt(token1.address):
        token0, token1 = token1, token0
    rewardToken = ERC20FixedSupply.deploy("REWARD", "REWARD", 2**120, root, {'from': root})
    tag0 = toInt(token0.address)
    tag1 = toInt(token1.address)

    startBlock = chain[-1].number + 50
    endBlock = chain[-1].number + 250

    incentiveDeploymentSalt = 12
    incentive = deployer.addressOf(incentiveDeploymentSalt)
    deployer.create3(
        incentiveDeploymentSalt,
        Incentive.bytecode + encode(
            ['address', 'address', 'address', 'address', 'address', 'uint256', 'uint256', 'address', 'address', 'uint32', 'uint32'],
            [nofeeswap.address, address0, address0, address0, root.address, toInt(token0.address), toInt(token1.address), incentive, rewardToken.address, startBlock, endBlock]
        ).hex(), 
        {'from': root}
    )
    incentive = Incentive.at(incentive)

    token0.approve(incentive, 2 ** 120, {'from': owner})
    token1.approve(incentive, 2 ** 120, {'from': owner})
    token0.approve(incentive, 2 ** 120, {'from': root})
    token1.approve(incentive, 2 ** 120, {'from': root})
    nofeeswap.setOperator(incentive, True, {'from': owner})

    kernel = [
      [0, 0],
      [2 ** 40, 2 ** 15]
    ]
    curve = [2 ** 50 + 1, 2 ** 50 + 1 + 2 ** 40]
    lower = min(curve[0], curve[1])
    upper = max(curve[0], curve[1])

    logOffset = -5
    unsaltedPoolId = (1 << 188) + (twosComplementInt8(logOffset) << 180) + (0b01000000001001001001 << 160) + toInt(incentive.address)
    poolId = getPoolId(root.address, unsaltedPoolId)

    tx = nofeeswap.dispatch(
      delegatee.initialize.encode_input(
          unsaltedPoolId,
          tag0,
          tag1,
          0x800000000000,
          encodeKernelCompact(kernel),
          encodeCurve(curve),
          b"HookData"
      ),
      {'from': root}
    )

    deadline = 2 ** 32 - 1
    hookData = encode(['uint256', 'address'], [0, owner.address])

    qMin = lower - (1 << 63) + (logOffset * (1 << 59))
    qMax = upper - (1 << 63) + (logOffset * (1 << 59))
    shares = 1000000
    tagShares = keccak(['uint256', 'int256', 'int256'], [poolId, qMin, qMax])

    data = mintIncentiveSequence(nofeeswap, incentive, token0, token1, tagShares, poolId, qMin, qMax, shares, hookData, deadline)
    tx = nofeeswap.unlock(incentive, data, {'from': owner})

    _poolId, _qMin, _qMax, _shares, _evanescentPointsPerShareSubtrahend, _evanescentPointsOwed = access._readIncentiveData(incentive, 1)

    assert _poolId == poolId
    assert _qMin == lower
    assert _qMax == upper
    assert _shares == shares
    assert _evanescentPointsPerShareSubtrahend == 0
    assert _evanescentPointsOwed == 0

    ###########################

    hookData = encode(['uint256', 'address'], [1, owner.address])

    data = mintIncentiveSequence(nofeeswap, incentive, token0, token1, tagShares, poolId, qMin, qMax, shares, hookData, deadline)
    tx = nofeeswap.unlock(incentive, data, {'from': root})

    _poolId, _logPriceMinOffsetted, _logPriceMaxOffsetted, _shares, _evanescentPointsPerShareSubtrahend, _evanescentPointsOwed = access._readIncentiveData(incentive, 1)

    assert _poolId == poolId
    assert _logPriceMinOffsetted == lower
    assert _logPriceMaxOffsetted == upper
    assert _shares == 2 * shares
    assert _evanescentPointsPerShareSubtrahend == 0
    assert _evanescentPointsOwed == 0

    ###########################

    sequence = [0] * 3
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, shares, 1]
    )
    sequence[1] = encode_packed(
      ['uint8', 'uint256', 'uint64', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [MODIFY_POSITION, poolId, lower - upper + lower, upper, 1, 0, 0, 0, len(hookData), hookData]
    )
    sequence[2] = encode_packed(
      ['uint8'],
      [REVERT]
    )
    data = encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence)
    with brownie.reverts('InvalidLogPriceMin: ' + str(lower) + ', ' + str(lower - upper + lower)):
        tx = nofeeswap.unlock(incentive, data, {'from': root})

    ###########################

    sequence = [0] * 3
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, shares, 1]
    )
    sequence[1] = encode_packed(
      ['uint8', 'uint256', 'uint64', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16','bytes'],
      [MODIFY_POSITION, poolId, lower, upper + upper - lower, 1, 0, 0, 0, len(hookData), hookData]
    )
    sequence[2] = encode_packed(
      ['uint8'],
      [REVERT]
    )
    data = encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence)
    with brownie.reverts('InvalidLogPriceMax: ' + str(upper) + ', ' + str(upper + upper - lower)):
        tx = nofeeswap.unlock(incentive, data, {'from': root})

    ###########################

    data = burnIncentiveSequence(token0, token1, owner, incentive, tagShares, poolId, qMin, qMax, 2 * shares, hookData, deadline)
    with brownie.reverts('OutstandingAmount: '):
        tx = nofeeswap.unlock(incentive, data, {'from': root})

    ###########################

    data = burnIncentiveSequence(token0, token1, owner, incentive, tagShares, poolId, qMin, qMax, 2 * shares, hookData, deadline)
    tx = nofeeswap.unlock(incentive, data, {'from': owner})

    _poolId, _logPriceMinOffsetted, _logPriceMaxOffsetted, _shares, _evanescentPointsPerShareSubtrahend, _evanescentPointsOwed = access._readIncentiveData(incentive, 1)

    assert _poolId == poolId
    assert _logPriceMinOffsetted == lower
    assert _logPriceMaxOffsetted == upper
    assert _shares == 0
    assert _evanescentPointsPerShareSubtrahend == 0
    assert _evanescentPointsOwed == 0

def test_permit(chain, deployment, request, worker_id):
    logTest(request, worker_id)
    
    root, owner, other, nofeeswap, delegatee, access, deployer, operator = deployment

    token0 = ERC20FixedSupply.deploy("ERC20_0", "ERC20_0", 2**120, owner, {'from': owner})
    token1 = ERC20FixedSupply.deploy("ERC20_1", "ERC20_1", 2**120, owner, {'from': owner})
    token0.approve(operator, 2** 120, {'from': owner})
    token1.approve(operator, 2** 120, {'from': owner})
    nofeeswap.setOperator(operator, True, {'from': owner})
    if toInt(token0.address) > toInt(token1.address):
        token0, token1 = token1, token0
    rewardToken = ERC20FixedSupply.deploy("REWARD", "REWARD", 2**120, root, {'from': root})
    tag0 = toInt(token0.address)
    tag1 = toInt(token1.address)

    startBlock = chain[-1].number + 50
    endBlock = chain[-1].number + 250

    incentiveDeploymentSalt = 13
    incentive = deployer.addressOf(incentiveDeploymentSalt)
    deployer.create3(
        incentiveDeploymentSalt,
        Incentive.bytecode + encode(
            ['address', 'address', 'address', 'address', 'address', 'uint256', 'uint256', 'address', 'address', 'uint32', 'uint32'],
            [nofeeswap.address, address0, address0, address0, root.address, toInt(token0.address), toInt(token1.address), incentive, rewardToken.address, startBlock, endBlock]
        ).hex(), 
        {'from': root}
    )
    incentive = Incentive.at(incentive)

    kernel = [
      [0, 0],
      [2 ** 40, 2 ** 15]
    ]
    curve = [2 ** 40 + 1, 2 ** 40 + 1 + 2 ** 40]
    lower = min(curve[0], curve[1])
    upper = max(curve[0], curve[1])

    logOffset = -5
    unsaltedPoolId = (1 << 188) + (twosComplementInt8(logOffset) << 180) + (0b01000000001001001001 << 160) + toInt(incentive.address)
    poolId = getPoolId(root.address, unsaltedPoolId)

    tx = nofeeswap.dispatch(
      delegatee.initialize.encode_input(
          unsaltedPoolId,
          tag0,
          tag1,
          0x800000000000,
          encodeKernelCompact(kernel),
          encodeCurve(curve),
          b"HookData"
      ),
      {'from': root}
    )

    deadline = 2 ** 32 - 1
    hookData = encode(['uint256', 'address'], [0, owner.address])

    qMin = lower - (1 << 63) + (logOffset * (1 << 59))
    qMax = upper - (1 << 63) + (logOffset * (1 << 59))
    shares = 1000000
    tagShares = keccak(['uint256', 'int256', 'int256'], [poolId, qMin, qMax])

    data = mintIncentiveSequence(nofeeswap, incentive, token0, token1, tagShares, poolId, qMin, qMax, shares, hookData, deadline)
    tx = nofeeswap.unlock(operator, data, {'from': owner})

    _poolId, _logPriceMinOffsetted, _logPriceMaxOffsetted, _shares, _evanescentPointsPerShareSubtrahend, _evanescentPointsOwed = access._readIncentiveData(incentive, 1)

    ##############################

    tokenId = 1
    wallet = accounts.add()
    incentive.transferFrom(owner, wallet, tokenId, {'from': owner})

    PERMIT_TYPEHASH = '0x49ecf333e5b8c95c40fdafc95c1ad136e8914a8fb55e9dc8bb01eaa83a2df9ad'
    domainSeparator = incentive.DOMAIN_SEPARATOR()
    nonce = 100
    deadline = 2 ** 256 - 1
    digest = keccak_256(encode_packed(
        ['bytes1', 'bytes1', 'bytes32', 'bytes32'],
        [
            brownie.convert.to_bytes('0x19', type_str='bytes1'),\
            brownie.convert.to_bytes('0x01', type_str='bytes1'),\
            domainSeparator,\
            keccak_256(encode(
                ['bytes32', 'address', 'uint256', 'uint256', 'uint256'],
                [brownie.convert.to_bytes(PERMIT_TYPEHASH, type_str='bytes32'), root.address, tokenId, nonce, deadline]
            )).digest()\
        ]
    ))

    signed = web3.eth.account.signHash(digest.hexdigest(), wallet.private_key)
    r = brownie.convert.to_bytes(signed.r, type_str='bytes32')
    s = brownie.convert.to_bytes(signed.s, type_str='bytes32')
    v = signed.v

    signature = encode_packed(['bytes32', 'bytes32', 'uint8'], [r, s, v])

    incentive.permit(root, tokenId, deadline, nonce, signature, {'from': root})
    incentive.transferFrom(wallet, root, tokenId, {'from': root})

def test_points(chain, deployment, request, worker_id):
    logTest(request, worker_id)
    
    root, owner, other, nofeeswap, delegatee, access, deployer, operator = deployment

    token0 = ERC20FixedSupply.deploy("ERC20_0", "ERC20_0", 2**120, owner, {'from': owner})
    token1 = ERC20FixedSupply.deploy("ERC20_1", "ERC20_1", 2**120, owner, {'from': owner})
    token0.approve(operator, 2**120, {'from': owner})
    token1.approve(operator, 2**120, {'from': owner})
    nofeeswap.setOperator(operator, True, {'from': owner})
    if toInt(token0.address) > toInt(token1.address):
        token0, token1 = token1, token0
    rewardToken = ERC20FixedSupply.deploy("REWARD", "REWARD", 2**120, root, {'from': root})
    tag0 = toInt(token0.address)
    tag1 = toInt(token1.address)

    startBlock = chain[-1].number + 50
    endBlock = chain[-1].number + 250

    incentiveDeploymentSalt = 14
    incentive = deployer.addressOf(incentiveDeploymentSalt)
    rewardToken.approve(incentive, 2**120, {'from': root})
    deployer.create3(
        incentiveDeploymentSalt,
        Incentive.bytecode + encode(
            ['address', 'address', 'address', 'address', 'address', 'uint256', 'uint256', 'address', 'address', 'uint32', 'uint32'],
            [nofeeswap.address, address0, address0, address0, root.address, toInt(token0.address), toInt(token1.address), root.address, rewardToken.address, startBlock, endBlock]
        ).hex(), 
        {'from': root}
    ) # startBlock - 49
    incentive = Incentive.at(incentive)

    ############################################################################

    spacing = 20 * 60 * 57643193118714
    kernel = [
      [0, 0],
      [spacing, 2 ** 15]
    ]
    curve = [
      (2 ** 63) - (spacing // 2) + spacing,
      (2 ** 63) - (spacing // 2),
      (2 ** 63)
    ]
    lower = min(curve[0], curve[1])
    upper = max(curve[0], curve[1])

    logOffset = -5
    unsaltedPoolId = (1 << 188) + (twosComplementInt8(logOffset) << 180) + (0b01000000001001001001 << 160) + toInt(incentive.address)
    poolId = getPoolId(root.address, unsaltedPoolId)

    tx = nofeeswap.dispatch(
      delegatee.initialize.encode_input(
          unsaltedPoolId,
          tag0,
          tag1,
          0x800000000000,
          encodeKernelCompact(kernel),
          encodeCurve(curve),
          b"HookData"
      ),
      {'from': root}
    ) # startBlock - 48

    ############################################################################

    deadline = 2 ** 32 - 1
    qMin = lower - (1 << 63) + (logOffset * (1 << 59))
    qMax = upper - (1 << 63) + (logOffset * (1 << 59))
    shares = 100000000000
    hookData = encode(['uint256', 'address'], [0, owner.address])
    tagShares = keccak(['uint256', 'int256', 'int256'], [poolId, qMin, qMax])

    data = mintIncentiveSequence(nofeeswap, incentive, token0, token1, tagShares, poolId, qMin, qMax, shares, hookData, deadline)
    tx = nofeeswap.unlock(operator, data, {'from': owner}) # startBlock - 47

    hookData = encode(['uint256', 'address'], [0, other.address])
    tagShares = keccak(['uint256', 'int256', 'int256'], [poolId, qMin, qMax])
    data = mintIncentiveSequence(nofeeswap, incentive, token0, token1, tagShares, poolId, qMin, qMax, 3 * shares, hookData, deadline)
    tx = nofeeswap.unlock(operator, data, {'from': owner}) # startBlock - 46

    ############################################################################

    chain.mine(49) # startBlock + 3

    ############################################################################

    staticParamsStoragePointerExtension, growth, integral0, integral1, sharesTotal, staticParamsStoragePointer, logPriceCurrent = access._readDynamicParams(nofeeswap, poolId)
    tag0, tag1, sqrtOffset, sqrtInverseOffset, sqrtSpacing, sqrtInverseSpacing = access._readStaticParams0(nofeeswap, poolId, staticParamsStoragePointer)
    outgoingMax, outgoingMaxModularInverse, incomingMax, poolGrowthPortion, maxPoolGrowthPortion, protocolGrowthPortion, pendingKernelLength = access._readStaticParams1(nofeeswap, poolId, staticParamsStoragePointer)

    amountSpecified = - (1 << 120)
    limit = upper - (spacing // 4) - (1 << 63) + (logOffset * (1 << 59))
    zeroForOne = 2
    hookData = b"HookData"

    data = swapSequence(nofeeswap, token0, token1, root, poolId, amountSpecified, limit, zeroForOne, hookData, deadline)
    tx = nofeeswap.unlock(operator, data, {'from': owner}) # startBlock + 4

    ############################################################################

    reward = floor(((chain[-1].number - startBlock) * growth * floor(sqrt(Integer(integral0 * integral1)) / (2 ** 104))) / Integer(outgoingMax)) * sharesTotal
    assert reward == access._readTotalEvanescentPointsOwedSlot(incentive)

    ############################################################################

    with brownie.reverts('ERC721InsufficientApproval: ' + root.address.lower() + ', ' + str(1)):
        tx = incentive.collect(1, {'from': root})

    ############################################################################

    tokenId = 1
    incentiveWrapper = IncentiveWrapper.deploy({'from': root})
    incentive.transferFrom(owner, incentiveWrapper, tokenId, {'from': owner})
    token0.transfer(incentiveWrapper, token0.balanceOf(owner), {'from': owner})
    token1.transfer(incentiveWrapper, token1.balanceOf(owner), {'from': owner})
    hookData = encode(['uint256', 'address'], [tokenId, incentiveWrapper.address])
    tx = incentiveWrapper.badCollect(
      nofeeswap,
      incentive,
      tokenId,
      token0,
      token1,
      mintIncentiveSequence(nofeeswap, incentive, token0, token1, tagShares, poolId, qMin, qMax, 1000 * shares, hookData, deadline),
      burnIncentiveSequence(token0, token1, incentiveWrapper, incentive, tagShares, poolId, qMin, qMax, 1000 * shares, hookData, deadline),
      {'from': root}
    )
    assert rewardToken.balanceOf(incentiveWrapper) == 2 ** 118

    ############################################################################

    incentive.collect(2, {'from': other})
    assert rewardToken.balanceOf(other) == 3 * (2 ** 118)