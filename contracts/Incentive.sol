// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {Strings} from "@openzeppelin/utils/Strings.sol";
import {IERC721Metadata} from "@openzeppelin/token/ERC721/ERC721.sol";
import {Multicall_v4} from "@uniswap/base/Multicall_v4.sol";
import {INofee} from "@governance/interfaces/INofee.sol";
import {Operator} from "@operator/Operator.sol";
import {StorageAccess} from "@core/StorageAccess.sol";
import {IHook} from "@core/interfaces/IHook.sol";
import {BaseHook} from "@core/hooks/BaseHook.sol";
import {INofeeswap} from "@core/interfaces/INofeeswap.sol";
import {Tag, TagLibrary} from "@core/utilities/Tag.sol";
import {FullMathLibrary} from "@core/utilities/FullMath.sol";
import {X59, sixteenX59} from "@core/utilities/X59.sol";
import {X111} from "@core/utilities/X111.sol";
import {X216} from "@core/utilities/X216.sol";
import {readStorage, writeStorage} from "@core/utilities/Storage.sol";
import {
  getPoolIdFromCalldata,
  getGrowthFromCalldata,
  getIntegral0FromCalldata,
  getIntegral1FromCalldata,
  getOutgoingMaxFromCalldata,
  getSharesTotalFromCalldata,
  getCurveFromCalldata,
  getMsgSenderFromCalldata,
  getTag0FromCalldata,
  getTag1FromCalldata,
  getLogPriceMinFromCalldata,
  getLogPriceMaxFromCalldata,
  getSharesFromCalldata,
  getLogPriceMinOffsettedFromCalldata,
  getLogPriceMaxOffsettedFromCalldata,
  getHookDataFromCalldata,
  getOutgoingMaxModularInverseFromCalldata
} from "@core/hooks/HookCalldata.sol";
import {Curve} from "@core/utilities/Curve.sol";
import {getLogOffsetFromPoolId} from "@core/utilities/PoolId.sol";

import {IIncentive} from "./interfaces/IIncentive.sol";
import {IIncentivePoolFactory} from "./interfaces/IIncentivePoolFactory.sol";
import {ERC721Permit} from "./base/ERC721Permit.sol";
import {geometricMean} from "./utilities/GeometricMean.sol";
import {
  incrementTokenId,
  getIncentiveDataSlot,
  readIncentiveData,
  writeIncentiveData,
  modifyIncentiveShares,
  collectEvanescentPoints,
  totalEvanescentPointsOwedSlot,
  getPoolDataSlot,
  readPoolData,
  getEvanescentPointsPerShareMappingSlot,
  updateTotalEvanescentPointsOwed,
  calculateEvanescentPointsPerShare,
  writePoolData
} from "./utilities/StorageIncentive.sol";

using TagLibrary for uint256;

/// @title Incentive hook distributes Nofee rewards to liquidity providers
/// of any subscribing pool. For each block and each subscribing pool, every LP
/// of the active liquidity interval is rewarded with evanescent points 
/// proportional to the following value per share:
///
///  growth * sqrt(integral0 * integral1)
/// --------------------------------------
///              outgoingMax
///
/// If the price is at the boundary of the active interval, then one of the
/// integrals is equal to zero and no LP is rewarded.
///
/// The total Nofee rewards for each LP is calculated as follows:
///
///                                       evanescentPointsCollected
/// rewardAmount = totalNofeeAllowance x ---------------------------
///                                       totalEvanescentPointsOwed
///
/// Rewards can be collected at any moment. However, the timing matters. LPs
/// who collect their rewards right after a Nofee deposit to this contract are
/// rewarded more.
contract Incentive is 
  IIncentive,
  BaseHook,
  Operator,
  StorageAccess,
  Multicall_v4,
  ERC721Permit('Nofeeswap Incentive', 'NOFEE-INCENTIVE')
{
  /// @inheritdoc IIncentive
  IIncentivePoolFactory public immutable override incentivePoolFactory;

  /// @inheritdoc IIncentive
  Tag public immutable override tag0;

  /// @inheritdoc IIncentive
  Tag public immutable override tag1;

  /// @inheritdoc IIncentive
  address public immutable override payMaster;

  /// @inheritdoc IIncentive
  INofee public immutable override rewardToken;

  /// @inheritdoc IIncentive
  uint32 public immutable override startBlock;

  /// @inheritdoc IIncentive
  uint32 public immutable override endBlock;

  /// @inheritdoc IIncentive
  X111 public immutable override maxIncentiveGrowth;

  constructor(
    INofeeswap _nofeeswap,
    address _permit2,
    address _weth9,
    address _quoter,
    IIncentivePoolFactory _incentivePoolFactory,
    Tag _tag0,
    Tag _tag1,
    address _payMaster,
    INofee _rewardToken,
    uint32 _startBlock,
    uint32 _endBlock,
    X111 _maxIncentiveGrowth
  ) Operator(address(_nofeeswap), _permit2, _weth9, _quoter) {
    incentivePoolFactory = _incentivePoolFactory;
    require(_tag0 < _tag1, TagsOutOfOrder(_tag0, _tag1));
    tag0 = _tag0;
    tag1 = _tag1;
    payMaster = _payMaster;
    rewardToken = _rewardToken;
    require(
      _startBlock > uint32(block.number),
      InvalidStartBlock(_startBlock, uint32(block.number))
    );
    startBlock = _startBlock;
    require(
      _endBlock > _startBlock,
      InvalidEndBlock(_endBlock, _startBlock)
    );
    endBlock = _endBlock;
    incrementTokenId();
    maxIncentiveGrowth = _maxIncentiveGrowth;
  }

  /// @inheritdoc IERC721Metadata
  function tokenURI(
    uint256 tokenId
  ) public view override returns (string memory) {
    uint256 storageSlot = getIncentiveDataSlot(tokenId);
    (
      uint256 poolId,
      X59 qMin,
      X59 qMax,
      uint256 shares,
      uint256 evanescentPointsPerShareSubtrahend,
      uint256 evanescentPointsOwed
    ) = readIncentiveData(storageSlot);

    X59 shift = getLogOffsetFromPoolId(poolId) - sixteenX59;

    return string(
      abi.encodePacked(
        ' PoolId: ', Strings.toHexString(poolId), '\\n',
        ' LogPriceMin: ', Strings.toStringSigned(
          X59.unwrap(qMin + shift)
        ), '\\n',
        ' LogPriceMax: ', Strings.toStringSigned(
          X59.unwrap(qMax + shift)
        ), '\\n'
        ' Shares: ', Strings.toString(shares), '\\n',
        ' EvanescentPointsPerShareSubtrahend: ', 
        Strings.toString(evanescentPointsPerShareSubtrahend), '\\n',
        ' EvanescentPointsOwed: ', 
        Strings.toString(evanescentPointsOwed), '\\n'
      )
    );
  }

  /// @inheritdoc IIncentive
  function collect(
    uint256 tokenId
  ) external override returns (
    uint256 amount
  ) {
    // Check token's ownership.
    _checkAuthorized(_ownerOf(tokenId), msg.sender, tokenId);

    // Update position data and read the total amount owned.
    uint256 evanescentPointsOwed = collectEvanescentPoints(tokenId);
    uint256 totalEvanescentPointsOwed = readStorage(
      totalEvanescentPointsOwedSlot
    );

    // Calculate the amount of reward to be collected.
    if (totalEvanescentPointsOwed != 0) {
      // 'mulDiv' is safe because 
      // 'evanescentPointsOwed <= totalEvanescentPointsOwed'.
      amount = FullMathLibrary.mulDiv(
        rewardToken.allowance(payMaster, address(this)),
        evanescentPointsOwed,
        totalEvanescentPointsOwed
      );
    }

    unchecked {
      // The subtraction is safe because 
      // 'evanescentPointsOwed <= totalEvanescentPointsOwed'.
      writeStorage(
        totalEvanescentPointsOwedSlot,
        totalEvanescentPointsOwed - evanescentPointsOwed
      );      
    }

    // Transfer the amount.
    rewardToken.transferFrom(payMaster, msg.sender, amount);
  }

  modifier onlyNofeeswap() {
    require(msg.sender == nofeeswap, OnlyByNofeeswap(msg.sender));
    _;
  }

  /// @inheritdoc IHook
  function preInitialize(
    bytes calldata hookInput
  ) external override(BaseHook, IHook) onlyNofeeswap returns (bytes4) {
    address msgSender = getMsgSenderFromCalldata();
    require(
      msgSender == address(incentivePoolFactory),
      InvalidFactory(msgSender)
    );

    Tag _tag0 = getTag0FromCalldata();
    require(_tag0 == tag0, InvalidTag0(_tag0));

    Tag _tag1 = getTag1FromCalldata();
    require(_tag1 == tag1, InvalidTag1(_tag1));

    uint256 poolId = getPoolIdFromCalldata();

    require(
      (
        (poolId & (0x5EFFF << 160)) == (0x40249 << 160)
      ) && (
        ((poolId & (1 << 179)) > 0) == ((poolId & (1 << 172)) > 0)
      ),
      IncompatibleFlags()
    );

    (X59 qLower, X59 qUpper) = _getBoundaries();

    uint32 blockNumber = uint32(block.number);

    writePoolData(
      getPoolDataSlot(poolId),
      blockNumber >= startBlock ? blockNumber : startBlock,
      qLower,
      qUpper,
      0
    );

    return IHook.preInitialize.selector;
  }

  /// @inheritdoc IHook
  function midMint(
    bytes calldata hookInput
  ) external override(BaseHook, IHook) onlyNofeeswap returns (bytes4) {
    // The calldata pointer for 'hookData' is loaded from which 'tokenId' and
    // 'recipient' are loaded.
    uint256 hookData = getHookDataFromCalldata();
    uint256 tokenId;
    address recipient;
    assembly {
      tokenId := calldataload(hookData)
      recipient := calldataload(add(hookData, 32))
    }

    // Accounting for evanescent points in the pool.
    _accountEvanescentPoints();

    // If no 'tokenId' is provided, a new NFT is issued.
    if (tokenId == 0) {
      _mint(
        getPoolIdFromCalldata(),
        getLogPriceMinOffsettedFromCalldata(),
        getLogPriceMaxOffsettedFromCalldata(),
        uint256(getSharesFromCalldata()),
        recipient
      );
    // Otherwise, the number of positions for the given 'tokenId' are
    // incremented.
    } else {
      require(_requireOwned(tokenId) == recipient, NotTokenOwner(recipient));

      modifyIncentiveShares(
        tokenId,
        calculateEvanescentPointsPerShare(
          getPoolIdFromCalldata(),
          getLogPriceMinOffsettedFromCalldata(),
          getLogPriceMaxOffsettedFromCalldata()
        ),
        getSharesFromCalldata()
      );
    }

    // Shares mint for 'address(this)' to be paid by the operator.
    INofeeswap(msg.sender).modifyBalance(
      address(this),
      getPoolIdFromCalldata().tag(
        getLogPriceMinFromCalldata(),
        getLogPriceMaxFromCalldata()
      ),
      getSharesFromCalldata()
    );

    return IHook.midMint.selector;
  }

  /// @inheritdoc IHook
  function midBurn(
    bytes calldata hookInput
  ) external override(BaseHook, IHook) onlyNofeeswap returns (bytes4) {
    // The calldata pointer for 'hookData' is loaded from which 'tokenId' and
    // 'recipient' are loaded.
    uint256 hookData = getHookDataFromCalldata();
    uint256 tokenId;
    address recipient;
    assembly {
      tokenId := calldataload(hookData)
      recipient := calldataload(add(hookData, 32))
    }

    // Checking the owner of 'tokenId'.
    require(_requireOwned(tokenId) == recipient, NotTokenOwner(recipient));

    // Accounting for evanescent points in the pool.
    _accountEvanescentPoints();

    // The number of positions for the given 'tokenId' are decremented.
    modifyIncentiveShares(
      tokenId,
      calculateEvanescentPointsPerShare(
        getPoolIdFromCalldata(),
        getLogPriceMinOffsettedFromCalldata(),
        getLogPriceMaxOffsettedFromCalldata()
      ),
      getSharesFromCalldata()
    );

    // Shares are transferred to 'recipient' to be burned by the operator.
    unchecked {
      Tag tag = getPoolIdFromCalldata().tag(
        getLogPriceMinFromCalldata(),
        getLogPriceMaxFromCalldata()
      );
      INofeeswap(msg.sender).modifyBalance(
        address(this),
        tag,
        getSharesFromCalldata()
      );
      INofeeswap(msg.sender).transferTransientBalanceFrom(
        address(this),
        recipient,
        tag,
        // The subtraction is safe because we are burning.
        uint256(0 - getSharesFromCalldata())
      );
    }

    return IHook.midBurn.selector;
  }

  /// @inheritdoc IHook
  function midSwap(
    bytes calldata hookInput
  ) external override(BaseHook, IHook) onlyNofeeswap returns (bytes4) {

    // Accounting for evanescent points in the pool.
    _accountEvanescentPoints();

    return IHook.midSwap.selector;
  }

  /// @inheritdoc IHook
  function midDonate(
    bytes calldata hookInput
  ) external override(BaseHook, IHook) onlyNofeeswap returns (bytes4) {

    // Accounting for evanescent points in the pool.
    _accountEvanescentPoints();

    return IHook.midDonate.selector;
  }

  /// @notice Updates 'totalEvanescentPointsOwed' and 
  /// 'evanescentPointsPerShareMapping'. Should be triggered with each 
  /// modifyPosition, swap, and donate.
  function _accountEvanescentPoints() internal {
    // Cache 'poolId'.
    uint256 poolId = getPoolIdFromCalldata();

    // Cache the current block and return if it is prior to the start of the
    // incentive program or if the incentive program is ended.
    uint32 currentBlock = uint32(block.number);
    if (currentBlock <= startBlock) return;
    if (endBlock < currentBlock) return;

    // Read the current pool's data and return if 'currentBlock' is equal to 
    // the last block in which the pool is touched.
    uint256 poolDataSlot = getPoolDataSlot(poolId);
    (
      uint32 lastBlockAccounted,
      X59 lastLower,
      X59 lastUpper,
      uint256 lastActiveEvanescentPointsPerShare
    ) = readPoolData(readStorage(poolDataSlot));
    if (currentBlock == lastBlockAccounted) return;

    // Read current active interval's boundaries from calldata.
    (X59 currentLower, X59 currentUpper) = _getBoundaries();

    // In this case, 'evanescentPointsPerShareMapping' needs to be updated.
    if (lastLower != currentLower) {
      uint256 pointsPerShareLowerSlot = getEvanescentPointsPerShareMappingSlot(
        poolId,
        lastLower
      );      
      uint256 pointsPerShareUpperSlot = getEvanescentPointsPerShareMappingSlot(
        poolId,
        lastUpper
      );
      uint256 pointsPerShareLower = readStorage(pointsPerShareLowerSlot);
      uint256 pointsPerShareUpper = readStorage(pointsPerShareUpperSlot);

      // In this case, the current active interval is ahead of the previous one.
      while (lastLower < currentLower) {
        unchecked {
          // The addition is safe because the number of points from '-infinity'
          // to 'lastUpper' is capped by 'totalEvanescentPointsOwed'.
          pointsPerShareLower += lastActiveEvanescentPointsPerShare;
        }

        writeStorage(pointsPerShareUpperSlot, pointsPerShareLower);

        unchecked {
          (lastLower, lastUpper) = (
            lastUpper,
            lastUpper + (lastUpper - lastLower)
          );          
        }

        pointsPerShareLowerSlot = pointsPerShareUpperSlot;
        pointsPerShareUpperSlot = getEvanescentPointsPerShareMappingSlot(
          poolId,
          lastUpper
        );

        uint256 pointsPerShareTransition = pointsPerShareUpper;

        pointsPerShareUpper = readStorage(pointsPerShareUpperSlot);

        unchecked {
          // Let 'l < t < u' denote the interval consecutive boundaries, 
          // respectively. The subtraction is safe, because the number of
          // points from 't' to '+infinity' is greater than or equal to the
          // number of points from 'u' to '+infinity'.
          lastActiveEvanescentPointsPerShare = 
            pointsPerShareTransition - pointsPerShareUpper;
        }
      }

      // In this case, the current active interval is prior to the previous one.
      while (currentLower < lastLower) {
        unchecked {
          // The addition is safe because the number of points from 'lastLower'
          // to '+infinity' is capped by 'totalEvanescentPointsOwed'.
          pointsPerShareUpper += lastActiveEvanescentPointsPerShare;
        }

        writeStorage(pointsPerShareLowerSlot, pointsPerShareUpper);

        unchecked {
          (lastLower, lastUpper) = (
            lastLower - (lastUpper - lastLower),
            lastLower
          );
        }

        pointsPerShareUpperSlot = pointsPerShareLowerSlot;
        pointsPerShareLowerSlot = getEvanescentPointsPerShareMappingSlot(
          poolId,
          lastLower
        );

        uint256 pointsPerShareTransition = pointsPerShareLower;

        pointsPerShareLower = readStorage(pointsPerShareLowerSlot);

        unchecked {
          // Let 'l < t < u' denote the interval consecutive boundaries, 
          // respectively. The subtraction is safe, because the number of
          // points from '-infinity' to 't' is greater than or equal to the
          // number of points from '-infinity' to 'l'.
          lastActiveEvanescentPointsPerShare = 
            pointsPerShareTransition - pointsPerShareLower;
        }
      }
    }

    // 'totalEvanescentPointsOwed' and 'lastActiveEvanescentPointsPerShare' are
    // updated.
    uint256 pointsPerShareIncrement;
    if (getGrowthFromCalldata() <= maxIncentiveGrowth) {
      unchecked {
        pointsPerShareIncrement = (currentBlock - lastBlockAccounted) * (
          geometricMean(
            getIntegral0FromCalldata(),
            getIntegral1FromCalldata()
          ) * uint256(X111.unwrap(getGrowthFromCalldata()))
        );
        uint256 outgoingMax = uint256(
          X216.unwrap(getOutgoingMaxFromCalldata())
        );
        uint256 twos = (0 - outgoingMax) & outgoingMax;
        pointsPerShareIncrement = (
          (
            pointsPerShareIncrement - (pointsPerShareIncrement % outgoingMax)
          ) / twos
        ) * getOutgoingMaxModularInverseFromCalldata();
        lastActiveEvanescentPointsPerShare += pointsPerShareIncrement;
      }
    }

    // Here, 'lastActiveEvanescentPointsPerShare' may never overflow because,
    // 
    //  'integral0 <= exp(- qLower / 2) * outgoingMax',
    //  'integral1 <= exp(- qUpper / 2) * outgoingMax',
    //  'blocks <= 2 ** 32',
    //  'growth <= 2 ** 127',
    //
    // Hence, we have:
    //
    //                                          (2 ** (32 + 127)) * exp(8)
    //  'lastActiveEvanescentPointsPerShare <= ----------------------------'
    //                                                  2 ** 104
    //
    writePoolData(
      poolDataSlot,
      currentBlock,
      currentLower,
      currentUpper,
      lastActiveEvanescentPointsPerShare
    );
    unchecked {
      // The multiplication is safe because 
      // 'pointsPerShareIncrement < type(uint96).max'
      updateTotalEvanescentPointsOwed(
        pointsPerShareIncrement * getSharesTotalFromCalldata()
      );
    }
  }

  /// @notice Provides the current active interval's boundaries by reading 
  /// the curve from calldata.
  function _getBoundaries() internal pure returns (
    X59 qLower,
    X59 qUpper
  ) {
    Curve curve = getCurveFromCalldata();
    assembly ("memory-safe") {
      qLower := shr(192, calldataload(curve))
      qUpper := and(shr(128, calldataload(curve)), 0xFFFFFFFFFFFFFFFF)
    }
    (qLower, qUpper) = qLower <= qUpper ? (qLower, qUpper) : (qUpper, qLower);
  }

  /// @notice Mints a new token for the owner.
  function _mint(
    uint256 poolId,
    X59 qMin,
    X59 qMax,
    uint256 shares,
    address owner
  ) internal returns (
    uint256 tokenId
  ) {
    tokenId = incrementTokenId();

    // Token's data is written.
    writeIncentiveData(
      getIncentiveDataSlot(tokenId),
      poolId,
      qMin,
      qMax,
      shares,
      calculateEvanescentPointsPerShare(poolId, qMin, qMax),
      0
    );

    // Token's owner is set to 'owner'.
    _mint(owner, tokenId);
  }
}