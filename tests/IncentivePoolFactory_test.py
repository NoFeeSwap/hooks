# Copyright 2025, NoFeeSwap LLC - All rights reserved.
import pytest
import brownie
from brownie import chain, accounts, Access, Nofeeswap, NofeeswapDelegatee, ERC20FixedSupply, Deployer, Operator, IncentivePoolFactory, Incentive
from Nofee import logTest, PUSH32, SWAP, REVERT, mintSequence, swapSequence, mintIncentiveSequence, keccak, address0, toInt, twosComplementInt8, encodeKernelCompact, encodeKernel, encodeCurve, getPoolId
from eth_abi import encode
from eth_abi.packed import encode_packed

@pytest.fixture(autouse=True)
def deployment(chain, fn_isolation):
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
    access = Access.deploy({'from': root})
    operator = Operator.deploy(nofeeswap, address0, address0, address0, {'from': root})

    nofeeswap.dispatch(delegatee.modifyProtocol.encode_input(
        (0x800000000000 << 208) + (0 << 160) + int(root.address, 16)
    ), {'from': root})

    totalSupply = 2**120

    t0 = ERC20FixedSupply.deploy("ERC20", "ERC20", totalSupply, root, {'from': root})
    t1 = ERC20FixedSupply.deploy("ERC20", "ERC20", totalSupply, root, {'from': root})
    t2 = ERC20FixedSupply.deploy("ERC20", "ERC20", totalSupply, root, {'from': root})

    t = [toInt(t0.address), toInt(t1.address), toInt(t2.address)]

    [token0, token1, rewardToken] = [x for _, x in sorted(zip(t, [t0, t1, t2]))]

    token0.approve(operator, totalSupply // 2, {'from': root})
    token1.approve(operator, totalSupply // 2, {'from': root})
    rewardToken.approve(operator, totalSupply // 2, {'from': root})

    deadline = 2 ** 32 - 1
    logOffset = 0
    spacing = 20 * 60 * 57643193118714
    kernel = [
      [0, 0],
      [spacing, 2 ** 15]
    ]
    curve = [
      (2 ** 63) - (spacing // 2),
      (2 ** 63) + spacing - (spacing // 2),
      (2 ** 63)
    ]
    lower = min(curve[0], curve[1])
    upper = max(curve[0], curve[1])

    return root, owner, other, token0, token1, rewardToken, nofeeswap, delegatee, operator, access, logOffset, lower, upper, curve, kernel, spacing, deadline

def test_incentivePoolFactory(deployment, request, worker_id):
    logTest(request, worker_id)
    
    root, owner, other, token0, token1, rewardToken, nofeeswap, delegatee, operator, access, logOffset, lower, upper, curve, kernel, spacing, deadline = deployment

    tag0 = toInt(token0.address)
    tag1 = toInt(token1.address)
    tagReward = toInt(rewardToken.address)

    incentivePoolFactory = IncentivePoolFactory.deploy(nofeeswap, rewardToken, other, owner, 1, 2, {'from': root})
    assert incentivePoolFactory.nofeeswap() == nofeeswap.address
    assert incentivePoolFactory.nofee() == rewardToken.address
    assert incentivePoolFactory.xNofee() == other.address
    assert incentivePoolFactory.admin() == owner.address
    assert incentivePoolFactory.disburseGap() == 1
    assert incentivePoolFactory.delay() == 2

    ###########################################

    unsaltedPoolId_TOKEN0_REWARD = (1 << 188) + (twosComplementInt8(logOffset) << 180) + (0b00000000001000000001 << 160) + toInt(incentivePoolFactory.address)
    poolId_TOKEN0_REWARD = getPoolId(root.address, unsaltedPoolId_TOKEN0_REWARD)

    with brownie.reverts('InvalidTags: ' + str(tag0) + ', ' + str(tag1)):
        tx = nofeeswap.dispatch(
          delegatee.initialize.encode_input(
              unsaltedPoolId_TOKEN0_REWARD,
              tag0,
              tag1,
              0,
              encodeKernelCompact(kernel),
              encodeCurve(curve),
              b""
          ),
          {'from': root}
        )

    tx = nofeeswap.dispatch(
      delegatee.initialize.encode_input(
          unsaltedPoolId_TOKEN0_REWARD,
          tag0,
          tagReward,
          0,
          encodeKernelCompact(kernel),
          encodeCurve(curve),
          b""
      ),
      {'from': root}
    )
    qMin = lower - (1 << 63) + (logOffset * (1 << 59))
    qMax = upper - (1 << 63) + (logOffset * (1 << 59))
    shares = 1000000000000000000000000000
    tagShares = keccak(['uint256', 'int256', 'int256'], [poolId_TOKEN0_REWARD, qMin, qMax])

    data = mintSequence(nofeeswap, token0, rewardToken, tagShares, poolId_TOKEN0_REWARD, qMin, qMax, shares, b"", deadline)
    tx = nofeeswap.unlock(operator, data, {'from': root})

    unsaltedPoolId_TOKEN1_REWARD = (2 << 188) + (twosComplementInt8(logOffset) << 180) + (0b00000000001000000001 << 160) + toInt(incentivePoolFactory.address)
    poolId_TOKEN1_REWARD = getPoolId(root.address, unsaltedPoolId_TOKEN1_REWARD)

    tx = nofeeswap.dispatch(
      delegatee.initialize.encode_input(
          unsaltedPoolId_TOKEN1_REWARD,
          tag1,
          tagReward,
          0,
          encodeKernelCompact(kernel),
          encodeCurve(curve),
          b""
      ),
      {'from': root}
    )
    qMin = lower - (1 << 63) + (logOffset * (1 << 59))
    qMax = upper - (1 << 63) + (logOffset * (1 << 59))
    shares = 1000000000000000000000000000
    tagShares = keccak(['uint256', 'int256', 'int256'], [poolId_TOKEN1_REWARD, qMin, qMax])

    data = mintSequence(nofeeswap, token1, rewardToken, tagShares, poolId_TOKEN1_REWARD, qMin, qMax, shares, b"", deadline)
    tx = nofeeswap.unlock(operator, data, {'from': root})

    ###########################################

    with brownie.reverts('OnlyByAdmin: ' + str(root.address.lower()) + ', ' + str(owner.address.lower())):
        incentivePoolFactory.setAdmin(root, {'from': root})

    tx = incentivePoolFactory.setAdmin(root, {'from': owner})
    assert incentivePoolFactory.admin() == root.address
    assert tx.events['NewAdmin']['oldAdmin'] == owner.address
    assert tx.events['NewAdmin']['newAdmin'] == root.address

    ###########################################

    disburseGap = 100
    with brownie.reverts('OnlyByAdmin: ' + str(owner.address.lower()) + ', ' + str(root.address.lower())):
        incentivePoolFactory.setDisburseGap(disburseGap, {'from': owner})
    tx = incentivePoolFactory.setDisburseGap(disburseGap, {'from': root})
    assert incentivePoolFactory.disburseGap() == disburseGap
    assert tx.events['NewDisburseGap']['oldDisburseGap'] == 1
    assert tx.events['NewDisburseGap']['newDisburseGap'] == disburseGap

    ###########################################

    delay = 20
    with brownie.reverts('OnlyByAdmin: ' + str(owner.address.lower()) + ', ' + str(root.address.lower())):
        incentivePoolFactory.setDelay(delay, {'from': owner})
    tx = incentivePoolFactory.setDelay(delay, {'from': root})
    assert incentivePoolFactory.delay() == delay
    assert tx.events['NewDelay']['oldDelay'] == 2
    assert tx.events['NewDelay']['newDelay'] == delay

    ###########################################

    poolGrowthPortionFactory = (2 ** 47) // 4

    with brownie.reverts("OnlyByAdmin: " + owner.address.lower() + ", " + root.address.lower()):
        tx = incentivePoolFactory.modifyPoolGrowthPortion([tag0], [tag1], [poolGrowthPortionFactory], {'from': owner})

    with brownie.reverts("TagsOutOfOrder: " + str(tag1) + ", " + str(tag0)):
        tx = incentivePoolFactory.modifyPoolGrowthPortion([tag1], [tag0], [poolGrowthPortionFactory], {'from': root})

    with brownie.reverts("UnequalLengths: " + str(1) + ", " + str(2)):
        tx =incentivePoolFactory.modifyPoolGrowthPortion([tag0], [tag1, tag1], [poolGrowthPortionFactory], {'from': root})

    with brownie.reverts("UnequalLengths: " + str(1) + ", " + str(2)):
        tx = incentivePoolFactory.modifyPoolGrowthPortion([tag0], [tag1], [poolGrowthPortionFactory, poolGrowthPortionFactory], {'from': root})

    assert incentivePoolFactory.poolGrowthPortion(tag0, tag1) == 0

    tx = incentivePoolFactory.modifyPoolGrowthPortion([tag0], [tag1], [poolGrowthPortionFactory], {'from': root})

    assert incentivePoolFactory.poolGrowthPortion(tag0, tag1) == poolGrowthPortionFactory
    assert tx.events['NewPoolGrowthPortions']['tag0'] == tag0
    assert tx.events['NewPoolGrowthPortions']['tag1'] == tag1
    assert tx.events['NewPoolGrowthPortions']['newPoolGrowthPortion'] == poolGrowthPortionFactory

    ###########################################

    with brownie.reverts("OnlyByAdmin: " + owner.address.lower() + ", " + root.address.lower()):
        tx = incentivePoolFactory.modifyConversionPools([poolId_TOKEN0_REWARD, poolId_TOKEN1_REWARD], {'from': owner})

    with brownie.reverts("InvalidConversionPool: 0"):
        tx = incentivePoolFactory.modifyConversionPools([poolId_TOKEN0_REWARD, 0], {'from': root})

    tx = incentivePoolFactory.modifyConversionPools([poolId_TOKEN0_REWARD, poolId_TOKEN1_REWARD], {'from': root})
    assert tx.events['NewConversionPool'][0]['tag'] == tag0
    assert tx.events['NewConversionPool'][0]['poolId'] == poolId_TOKEN0_REWARD
    assert tx.events['NewConversionPool'][1]['tag'] == tag1
    assert tx.events['NewConversionPool'][1]['poolId'] == poolId_TOKEN1_REWARD

    assert incentivePoolFactory.conversionPools(tag0) == poolId_TOKEN0_REWARD
    assert incentivePoolFactory.conversionPools(tag1) == poolId_TOKEN1_REWARD

    ###########################################

    startBlock = chain[-1].number + 50
    endBlock = chain[-1].number + 250

    incentive = Incentive.deploy(
        nofeeswap.address,
        address0,
        address0,
        address0,
        incentivePoolFactory.address,
        tag0,
        tag1,
        other.address,
        rewardToken.address,
        startBlock,
        endBlock,
        {'from': root}
    )

    unpepperdPoolId_TOKEN0_TOKEN1 = (3 << 188) + (twosComplementInt8(logOffset) << 180) + (0b11100001001001001001 << 160) + toInt(incentive.address)
    unsaltedPoolId_TOKEN0_TOKEN1 = getPoolId(owner.address, unpepperdPoolId_TOKEN0_TOKEN1)
    poolId_TOKEN0_TOKEN1 = getPoolId(incentivePoolFactory.address, unsaltedPoolId_TOKEN0_TOKEN1)
    incentivePoolFactory.initialize(
        unpepperdPoolId_TOKEN0_TOKEN1,
        encodeKernelCompact(kernel),
        encodeCurve(curve),
        {'from': owner}
    )
    qMin = lower - (1 << 63) + (logOffset * (1 << 59))
    qMax = upper - (1 << 63) + (logOffset * (1 << 59))
    shares = 1000000000000000000000000000
    tagShares = keccak(['uint256', 'int256', 'int256'], [poolId_TOKEN0_TOKEN1, qMin, qMax])

    staticParamsStoragePointerExtension, growth, integral0, integral1, sharesTotal, staticParamsStoragePointer, logPriceCurrent = access._readDynamicParams(nofeeswap, poolId_TOKEN0_TOKEN1)
    tag0, tag1, sqrtOffset, sqrtInverseOffset, sqrtSpacing, sqrtInverseSpacing = access._readStaticParams0(nofeeswap, poolId_TOKEN0_TOKEN1, staticParamsStoragePointer)
    outgoingMax, outgoingMaxModularInverse, incomingMax, poolGrowthPortion, maxPoolGrowthPortion, protocolGrowthPortion, pendingKernelLength = access._readStaticParams1(nofeeswap, poolId_TOKEN0_TOKEN1, staticParamsStoragePointer)
    assert poolGrowthPortion == poolGrowthPortionFactory
    assert incentivePoolFactory.balanceOf(owner) == 1
    assert incentivePoolFactory.ownerOf(poolId_TOKEN0_TOKEN1) == owner.address

    ###########################################

    poolGrowthPortionFactory = (3 * (2 ** 47)) // 4

    tx = incentivePoolFactory.modifyPoolGrowthPortion([tag0], [tag1], [poolGrowthPortionFactory], {'from': root})

    assert incentivePoolFactory.poolGrowthPortion(tag0, tag1) == poolGrowthPortionFactory
    assert tx.events['NewPoolGrowthPortions']['tag0'] == tag0
    assert tx.events['NewPoolGrowthPortions']['tag1'] == tag1
    assert tx.events['NewPoolGrowthPortions']['newPoolGrowthPortion'] == poolGrowthPortionFactory

    incentivePoolFactory.updatePoolGrowthPortion([poolId_TOKEN0_TOKEN1], {'from': other})

    staticParamsStoragePointerExtension, growth, integral0, integral1, sharesTotal, staticParamsStoragePointer, logPriceCurrent = access._readDynamicParams(nofeeswap, poolId_TOKEN0_TOKEN1)
    tag0, tag1, sqrtOffset, sqrtInverseOffset, sqrtSpacing, sqrtInverseSpacing = access._readStaticParams0(nofeeswap, poolId_TOKEN0_TOKEN1, staticParamsStoragePointer)
    outgoingMax, outgoingMaxModularInverse, incomingMax, poolGrowthPortion, maxPoolGrowthPortion, protocolGrowthPortion, pendingKernelLength = access._readStaticParams1(nofeeswap, poolId_TOKEN0_TOKEN1, staticParamsStoragePointer)
    assert poolGrowthPortion == poolGrowthPortionFactory

    ###########################################

    kernel = [
      [0, 0],
      [spacing // 2, 0],
      [spacing // 2, 2 ** 15],
      [spacing, 2 ** 15]
    ]

    with brownie.reverts("ERC721InsufficientApproval: " + root.address.lower() + ", " + str(poolId_TOKEN0_TOKEN1)):
        incentivePoolFactory.modifyKernel(
            poolId_TOKEN0_TOKEN1,
            encodeKernelCompact(kernel),
            {'from': root}
        )

    incentivePoolFactory.modifyKernel(
        poolId_TOKEN0_TOKEN1,
        encodeKernelCompact(kernel),
        {'from': owner}
    )

    staticParamsStoragePointerExtension, growth, integral0, integral1, sharesTotal, staticParamsStoragePointer, logPriceCurrent = access._readDynamicParams(nofeeswap, poolId_TOKEN0_TOKEN1)
    tag0, tag1, sqrtOffset, sqrtInverseOffset, sqrtSpacing, sqrtInverseSpacing = access._readStaticParams0(nofeeswap, poolId_TOKEN0_TOKEN1, staticParamsStoragePointer)
    outgoingMax, outgoingMaxModularInverse, incomingMax, poolGrowthPortion, maxPoolGrowthPortion, protocolGrowthPortion, pendingKernelLength = access._readStaticParams1(nofeeswap, poolId_TOKEN0_TOKEN1, staticParamsStoragePointer)
    assert encodeKernel(kernel) == list(access._readKernel(nofeeswap, poolId_TOKEN0_TOKEN1, staticParamsStoragePointer + 1))

    ###########################################

    hookData = encode(['uint256', 'address'], [0, owner.address])
    data = mintIncentiveSequence(nofeeswap, incentive, token0, token1, tagShares, poolId_TOKEN0_TOKEN1, qMin, qMax, shares, hookData, deadline)
    tx = nofeeswap.unlock(operator, data, {'from': root})

    target = [0] * 8
    target[0] = lower + 1*(spacing // 8)
    target[1] = upper - 1*(spacing // 8)
    target[2] = lower + 2*(spacing // 8)
    target[3] = upper - 2*(spacing // 8)
    target[4] = lower + 3*(spacing // 8)
    target[5] = upper - 3*(spacing // 8)
    target[6] = lower
    target[7] = upper

    for k in range(len(target)):
        amountSpecified = - (1 << 125)
        limit = target[k] - (1 << 63) + (logOffset * (1 << 59))
        zeroForOne = 2
        hookData = b"HookData"

        data = swapSequence(nofeeswap, token0, token1, root, poolId_TOKEN0_TOKEN1, amountSpecified, limit, zeroForOne, b"", deadline)
        tx = nofeeswap.unlock(operator, data, {'from': root})

    tx = nofeeswap.dispatch(
        delegatee.collectPool.encode_input(poolId_TOKEN0_TOKEN1), {'from': root}
    )

    chain.mine(disburseGap)

    tx = incentivePoolFactory.disburse(tag0, {'from': root})
    _amount0, nofeeAmount0 = tx.return_value
    tx = incentivePoolFactory.disburse(tag1, {'from': root})
    _amount1, nofeeAmount1 = tx.return_value
    assert rewardToken.balanceOf(other) == nofeeAmount0 + nofeeAmount1

    ###########################################

    blockNumber = chain[-1].number
    for k in range(len(target)):
        amountSpecified = - (1 << 125)
        limit = target[k] - (1 << 63) + (logOffset * (1 << 59))
        zeroForOne = 2
        hookData = b"HookData"

        data = swapSequence(nofeeswap, token0, token1, root, poolId_TOKEN0_TOKEN1, amountSpecified, limit, zeroForOne, b"", deadline)
        tx = nofeeswap.unlock(operator, data, {'from': root})

    tx = nofeeswap.dispatch(
        delegatee.collectPool.encode_input(poolId_TOKEN0_TOKEN1), {'from': root}
    )

    with brownie.reverts('TooEarlyToDisburse: ' + str(blockNumber - 1 + disburseGap) + ', ' + str(chain[-1].number + 1)):
        tx = incentivePoolFactory.disburse(tag0, {'from': root})

    with brownie.reverts('TooEarlyToDisburse: ' + str(blockNumber + disburseGap) + ', ' + str(chain[-1].number + 1)):
        tx = incentivePoolFactory.disburse(tag1, {'from': root})

    chain.mine(disburseGap)

    tx = incentivePoolFactory.disburse(tag0, {'from': root})
    amount0_, _nofeeAmount0 = tx.return_value
    tx = incentivePoolFactory.disburse(tag1, {'from': root})
    amount1_, _nofeeAmount1 = tx.return_value
    assert rewardToken.balanceOf(other) == nofeeAmount0 + nofeeAmount1 + _nofeeAmount0 + _nofeeAmount1

    amountSpecified = 1000
    zeroForOne = 2

    slot = 100

    sequence = [0] * 3
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, amountSpecified, slot]
    )
    sequence[2] = encode_packed(
      ['uint8'],
      [REVERT]
    )

    if tag0 < tagReward:
        sequence[1] = encode_packed(
          ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
          [SWAP, poolId_TOKEN0_REWARD, slot, upper, zeroForOne, slot, slot, slot, slot, len(hookData), hookData]
        )
    else:
        sequence[1] = encode_packed(
          ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
          [SWAP, poolId_TOKEN0_REWARD, slot, lower, zeroForOne, slot, slot, slot, slot, len(hookData), hookData]
        )

    with brownie.reverts('PoolIsClosedForThisDirection: ' + str(poolId_TOKEN0_REWARD) + ', ' + str(chain[-1].number + delay - 1) + ', ' + str(chain[-1].number + 1)):
        tx = nofeeswap.unlock(operator, encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence), {'from': root})

    if tag1 < tagReward:
        sequence[1] = encode_packed(
          ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
          [SWAP, poolId_TOKEN1_REWARD, slot, upper, zeroForOne, slot, slot, slot, slot, len(hookData), hookData]
        )
    else:
        sequence[1] = encode_packed(
          ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
          [SWAP, poolId_TOKEN1_REWARD, slot, lower, zeroForOne, slot, slot, slot, slot, len(hookData), hookData]
        )
    
    with brownie.reverts('PoolIsClosedForThisDirection: ' + str(poolId_TOKEN1_REWARD) + ', ' + str(chain[-1].number + delay - 1) + ', ' + str(chain[-1].number + 1)):
        tx = nofeeswap.unlock(operator, encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence), {'from': root})

    chain.mine(delay)

    staticParamsStoragePointerExtension, growth, integral0, integral1, sharesTotal, staticParamsStoragePointer, _logPriceCurrent = access._readDynamicParams(nofeeswap, poolId_TOKEN0_REWARD)
    if tag0 < tagReward:
        data = swapSequence(nofeeswap, token0, rewardToken, root, poolId_TOKEN0_REWARD, 1 << 90, lower, zeroForOne, b"", deadline)
    else:
        data = swapSequence(nofeeswap, rewardToken, token0, root, poolId_TOKEN0_REWARD, 1 << 90, upper, zeroForOne, b"", deadline)
    tx = nofeeswap.unlock(operator, data, {'from': root})
    staticParamsStoragePointerExtension, growth, integral0, integral1, sharesTotal, staticParamsStoragePointer, logPriceCurrent = access._readDynamicParams(nofeeswap, poolId_TOKEN0_REWARD)
    assert logPriceCurrent != _logPriceCurrent
    
    staticParamsStoragePointerExtension, growth, integral0, integral1, sharesTotal, staticParamsStoragePointer, _logPriceCurrent = access._readDynamicParams(nofeeswap, poolId_TOKEN1_REWARD)
    if tag1 < tagReward:
        data = swapSequence(nofeeswap, token1, rewardToken, root, poolId_TOKEN1_REWARD, 1 << 90, lower, zeroForOne, b"", deadline)
    else:
        data = swapSequence(nofeeswap, rewardToken, token1, root, poolId_TOKEN1_REWARD, 1 << 90, upper, zeroForOne, b"", deadline)    
    tx = nofeeswap.unlock(operator, data, {'from': root})
    staticParamsStoragePointerExtension, growth, integral0, integral1, sharesTotal, staticParamsStoragePointer, logPriceCurrent = access._readDynamicParams(nofeeswap, poolId_TOKEN1_REWARD)
    assert logPriceCurrent != _logPriceCurrent