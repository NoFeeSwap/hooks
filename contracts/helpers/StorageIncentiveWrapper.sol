// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import "../utilities/StorageIncentive.sol";

/// @title This contract exposes the internal functions of
/// 'StorageIncentive.sol' for testing purposes.
contract StorageIncentiveWrapper {
  function _tokenIdSlot() public returns (
    uint256 storageSlot
  ) {
    return tokenIdSlot;
  }

  function _incrementTokenId(
    uint256 tokenId,
    uint256 storageSlot
  ) public returns (
    uint256 tokenIdOld,
    uint256 tokenIdNew
  ) {
    writeStorage(tokenIdSlot, tokenId);
    tokenIdOld = incrementTokenId();
    tokenIdNew = readStorage(tokenIdSlot);
  }

  function _totalEvanescentPointsOwedSlot() public returns (
    uint256 storageSlot
  ) {
    return totalEvanescentPointsOwedSlot;
  }

  function _updateTotalEvanescentPointsOwed(
    uint256 totalEvanescentPointsOwed,
    uint256 increment
  ) public returns (
    uint256 totalEvanescentPointsOwedIncremented
  ) {
    writeStorage(totalEvanescentPointsOwedSlot, totalEvanescentPointsOwed);
    updateTotalEvanescentPointsOwed(increment);
    return readStorage(totalEvanescentPointsOwedSlot);
  }

  function _poolDataSlot() public returns (
    uint256 storageSlot
  ) {
    return poolDataSlot;
  }

  function _getPoolDataSlot(
    uint256 poolId
  ) public returns (
    uint256 storageSlot
  ) {
    return getPoolDataSlot(poolId);
  }

  function _readPoolData(
    uint256 value
  ) public returns (
    uint32 blockNumber,
    X59 qLower,
    X59 qUpper,
    uint256 activeEvanescentPointsPerShare
  ) {
    return readPoolData(value);
  }

  function _writePoolData(
    uint256 storageSlot,
    uint32 blockNumber,
    X59 qLower,
    X59 qUpper,
    uint256 activeEvanescentPointsPerShare
  ) public returns (
    uint256 content
  ) {
    writePoolData(
      storageSlot,
      blockNumber,
      qLower,
      qUpper,
      activeEvanescentPointsPerShare
    );
    return readStorage(storageSlot);
  }

  function _incentiveDataSlot() public returns (
    uint256 storageSlot
  ) {
    return incentiveDataSlot;
  }

  function _getIncentiveDataSlot(
    uint256 tokenId
  ) public returns (
    uint256 storageSlot
  ) {
    return getIncentiveDataSlot(tokenId);
  }

  function _readIncentiveData(
    uint256 storageSlot,
    uint256 content0,
    uint256 content1,
    uint256 content2
  ) public returns (
    uint256 poolId,
    X59 qMin,
    X59 qMax,
    uint256 shares,
    uint256 evanescentPointsPerShareSubtrahend,
    uint256 evanescentPointsOwed
  ) {
    unchecked {
      writeStorage(storageSlot + 0, content0);
      writeStorage(storageSlot + 1, content1);
      writeStorage(storageSlot + 2, content2);      
    }
    return readIncentiveData(storageSlot);
  }

  function _modifyIncentiveShares(
    uint256 tokenId,
    uint256 evanescentPointsPerShare,
    int256 sharesIncrement,
    uint256 content0,
    uint256 content1,
    uint256 content2
  ) public returns (
    uint256 content0New,
    uint256 content1New,
    uint256 content2New
  ) {
    unchecked {
      uint256 storageSlot = getIncentiveDataSlot(tokenId);
      writeStorage(storageSlot + 0, content0);
      writeStorage(storageSlot + 1, content1);
      writeStorage(storageSlot + 2, content2);
      modifyIncentiveShares(tokenId, evanescentPointsPerShare, sharesIncrement);
      content0New = readStorage(storageSlot + 0);
      content1New = readStorage(storageSlot + 1);
      content2New = readStorage(storageSlot + 2);
    }
  }

  function _collectEvanescentPoints(
    uint256 tokenId,
    uint256 content0,
    uint256 content1,
    uint256 content2,
    uint256 value,
    uint256[] calldata storageSlots,
    uint256[] calldata contents
  ) public returns (
    uint256 evanescentPointsOwed,
    uint256 content0New,
    uint256 content1New,
    uint256 content2New
  ) {
    unchecked {
      uint256 storageSlot = getIncentiveDataSlot(tokenId);
      writeStorage(storageSlot + 0, content0);
      writeStorage(storageSlot + 1, content1);
      writeStorage(storageSlot + 2, content2);
      writeStorage(
        getPoolDataSlot(
          (
            content0 & (0xffffffffffffffffffffffff << 160)
          ) + uint256(uint160(address(this)))
        ),
        value
      );
      for (uint256 kk = 0; kk < storageSlots.length; kk++) {
        writeStorage(storageSlots[kk], contents[kk]);
      }
      evanescentPointsOwed = collectEvanescentPoints(tokenId);
      content0New = readStorage(storageSlot + 0);
      content1New = readStorage(storageSlot + 1);
      content2New = readStorage(storageSlot + 2);
    }
  }

  function _writeIncentiveData(
    uint256 storageSlot,
    uint256 poolId,
    X59 qMin,
    X59 qMax,
    uint256 shares,
    uint256 evanescentPointsPerShareSubtrahend,
    uint256 evanescentPointsOwed
  ) public returns (
    uint256 content0,
    uint256 content1,
    uint256 content2
  ) {
    writeIncentiveData(
      storageSlot,
      poolId,
      qMin,
      qMax,
      shares,
      evanescentPointsPerShareSubtrahend,
      evanescentPointsOwed
    );
    unchecked {
      content0 = readStorage(storageSlot + 0);
      content1 = readStorage(storageSlot + 1);
      content2 = readStorage(storageSlot + 2);      
    }
  }

  function _evanescentPointsPerShareMappingSlot() public returns (
    uint256 storageSlot
  ) {
    return evanescentPointsPerShareMappingSlot;
  }

  function _getEvanescentPointsPerShareMappingSlot(
    uint256 poolId,
    X59 logPrice
  ) public returns (
    uint256 storageSlot
  ) {
    return getEvanescentPointsPerShareMappingSlot(poolId, logPrice);
  }

  function _calculateEvanescentPointsPerShare(
    uint256 poolId,
    X59 qMin,
    X59 qMax,
    uint256 value,
    uint256[] calldata storageSlots,
    uint256[] calldata contents
  ) public returns (
    uint256 evanescentPointsPerShare
  ) {
    writeStorage(getPoolDataSlot(poolId), value);
    for (uint256 kk = 0; kk < storageSlots.length; kk++) {
      writeStorage(storageSlots[kk], contents[kk]);
    }
    return calculateEvanescentPointsPerShare(poolId, qMin, qMax);
  }
}