// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {IUnlockCallback} from "@core/callback/IUnlockCallback.sol";
import {IHook} from "@core/interfaces/IHook.sol";
import {INofee} from "@governance/interfaces/INofee.sol";
import {IXNofee} from "@vault/interfaces/IXNofee.sol";
import {BaseHook} from "@core/hooks/BaseHook.sol";
import {ERC721} from "@openzeppelin/token/ERC721/ERC721.sol";
import {INofeeswap} from "@core/interfaces/INofeeswap.sol";
import {INofeeswapDelegatee} from "@core/interfaces/INofeeswapDelegatee.sol";
import {Tag, TagLibrary} from "@core/utilities/Tag.sol";
import {X47, oneX47} from "@core/utilities/X47.sol";
import {minX59, maxX59} from "@core/utilities/X59.sol";
import {getStaticParamsStorageAddress} from "@core/utilities/Storage.sol";
import {
  getTag0FromCalldata,
  getTag1FromCalldata,
  getPoolIdFromCalldata,
  getZeroForOneFromCalldata
} from "@core/hooks/HookCalldata.sol";
import {IIncentivePoolFactory} from "./interfaces/IIncentivePoolFactory.sol";
import {IIncentive} from "./interfaces/IIncentive.sol";

using TagLibrary for address;

contract IncentivePoolFactory is 
  IIncentivePoolFactory,
  BaseHook,
  ERC721('Nofeeswap IncentivePoolFactory', 'NOFEE-INCENTIVE-POOL-FACTORY')
{
  /// @inheritdoc IIncentivePoolFactory
  INofeeswap public immutable override nofeeswap;

  /// @inheritdoc IIncentivePoolFactory
  INofee public immutable override nofee;

  /// @inheritdoc IIncentivePoolFactory
  IXNofee public immutable override xNofee;

  /// @inheritdoc IIncentivePoolFactory
  address public override admin;

  /// @inheritdoc IIncentivePoolFactory
  uint256 public override disburseGap;

  /// @inheritdoc IIncentivePoolFactory
  uint256 public override delay;

  /// @inheritdoc IIncentivePoolFactory
  mapping(
    Tag tag0 => mapping(Tag tag1 => X47)
  ) public override poolGrowthPortion;

  /// @inheritdoc IIncentivePoolFactory
  mapping(Tag tag => uint256 poolId) public override conversionPools;

  /// @inheritdoc IIncentivePoolFactory
  mapping(Tag tag => uint256 blockNumber) public override lastDisbursed;

  constructor(
    INofeeswap _nofeeswap,
    INofee _nofee,
    IXNofee _xNofee,
    address _admin,
    uint256 _disburseGap,
    uint256 _delay
  ) {
    nofeeswap = _nofeeswap;
    nofee = _nofee;
    xNofee = _xNofee;
    admin = _admin;
    disburseGap = _disburseGap;
    delay = _delay;
  }

  /// @notice Prevents any address other than 'admin' to call this function.
  modifier onlyAdmin() {
    address admin_ = admin;
    require(msg.sender == admin_, OnlyByAdmin(msg.sender, admin_));
    _;
  }

  /// @inheritdoc IIncentivePoolFactory
  function setAdmin(address _admin) external override onlyAdmin {
    emit NewAdmin(admin, _admin);
    admin = _admin;
  }

  /// @inheritdoc IIncentivePoolFactory
  function setDisburseGap(uint256 _disburseGap) external override onlyAdmin {
    emit NewDisburseGap(disburseGap, _disburseGap);
    disburseGap = _disburseGap;
  }

  /// @inheritdoc IIncentivePoolFactory
  function setDelay(uint256 _delay) external override onlyAdmin {
    emit NewDelay(delay, _delay);
    delay = _delay;
  }

  /// @inheritdoc IIncentivePoolFactory
  function modifyPoolGrowthPortion(
    Tag[] calldata tag0,
    Tag[] calldata tag1,
    X47[] calldata newPoolGrowthPortion
  ) external override onlyAdmin {
    require(
      tag0.length == tag1.length,
      UnequalLengths(tag0.length, tag1.length)
    );
    require(
      tag0.length == newPoolGrowthPortion.length,
      UnequalLengths(tag0.length, newPoolGrowthPortion.length)
    );
    
    unchecked {
      for (uint256 k = 0; k < tag0.length; ++k) {
        require(tag0[k] < tag1[k], TagsOutOfOrder(tag0[k], tag1[k]));
        require(
          newPoolGrowthPortion[k] <= oneX47,
          InvalidGrowthPortion(newPoolGrowthPortion[k])
        );
        poolGrowthPortion[tag0[k]][tag1[k]] = newPoolGrowthPortion[k];
        emit NewPoolGrowthPortions(tag0[k], tag1[k], newPoolGrowthPortion[k]);
      }      
    }
  }

  /// @inheritdoc IIncentivePoolFactory
  function modifyConversionPools(
    uint256[] memory poolIds
  ) external override onlyAdmin {
    unchecked {
      uint256 length = poolIds.length;
      for (uint256 k = 0; k < length; ++k) {
        uint256 poolId = poolIds[k];
        require(
          address(uint160(poolId)) == address(this),
          InvalidConversionPool(poolId)
        );
        (Tag tag0, Tag tag1) = _readTags(poolId);
        if (tag0 == address(nofee).tag()) {
          conversionPools[tag1] = poolId;
          emit NewConversionPool(tag1, poolId);
        } else {
          conversionPools[tag0] = poolId;
          emit NewConversionPool(tag0, poolId);
        }
      }
    }
  }

  /// @inheritdoc IIncentivePoolFactory
  function updatePoolGrowthPortion(
    uint256[] memory poolIds
  ) external override {
    unchecked {
      uint256 length = poolIds.length;
      for (uint256 k = 0; k < length; ++k) {
        uint256 poolId = poolIds[k];
        (Tag tag0, Tag tag1) = _readTags(poolId);
        INofeeswap(nofeeswap).dispatch(
          abi.encodeWithSelector(
            INofeeswapDelegatee.modifyPoolGrowthPortion.selector,
            poolId,
            poolGrowthPortion[tag0][tag1]
          )
        );
      }
    }
  }

  /// @inheritdoc IIncentivePoolFactory
  function initialize(
    uint256 unpepperedPoolId,
    uint256[] calldata kernelCompactArray,
    uint256[] calldata curveArray
  ) external override {
    uint256 unsaltedPoolId;
    unchecked {
      unsaltedPoolId = unpepperedPoolId + uint256(
        keccak256(abi.encodePacked(msg.sender, unpepperedPoolId)) << 188
      );
    }
    Tag tag0 = IIncentive(address(uint160(unpepperedPoolId))).tag0();
    Tag tag1 = IIncentive(address(uint160(unpepperedPoolId))).tag1();
    INofeeswap(nofeeswap).dispatch(
      abi.encodeWithSelector(
        INofeeswapDelegatee.initialize.selector,
        unsaltedPoolId,
        tag0,
        tag1,
        poolGrowthPortion[tag0][tag1],
        kernelCompactArray,
        curveArray,
        ""
      )
    );
    uint256 poolId;
    unchecked {
      poolId = unsaltedPoolId + uint256(
        keccak256(abi.encodePacked(address(this), unsaltedPoolId)) << 188
      );
    }
    _mint(msg.sender, poolId);
  }

  /// @inheritdoc IIncentivePoolFactory
  function modifyKernel(
    uint256 poolId,
    uint256[] calldata kernelCompactArray
  ) external override {
    _checkAuthorized(_ownerOf(poolId), msg.sender, poolId);
    INofeeswap(nofeeswap).dispatch(
      abi.encodeWithSelector(
        INofeeswapDelegatee.modifyKernel.selector,
        poolId,
        kernelCompactArray,
        ""
      )
    );
  }

  /// @inheritdoc IIncentivePoolFactory
  function disburse(
    Tag tag
  ) external override returns (
    uint256 amount,
    uint256 nofeeAmount
  ) {
    uint256 nextDisbursementBlock = lastDisbursed[tag] + disburseGap;
    require(
      nextDisbursementBlock <= block.number,
      TooEarlyToDisburse(nextDisbursementBlock, block.number)
    );
    lastDisbursed[tag] = block.number;

    amount = INofeeswap(nofeeswap).balanceOf(address(this), tag);

    // Unlocking nofeeswap in order to perform swaps.
    nofeeAmount = abi.decode(
      INofeeswap(nofeeswap).unlock(
        address(this),
        abi.encode(tag, amount)
      ),
      (uint256)
    );
  }

  modifier onlyNofeeswap() {
    require(INofeeswap(msg.sender) == nofeeswap, OnlyByNofeeswap(msg.sender));
    _;
  }

  /// @inheritdoc IUnlockCallback
  function unlockCallback(
    address caller,
    bytes calldata data
  ) external payable override onlyNofeeswap returns (bytes memory ) {
    require(caller == address(this), CallerMustBeIncentivePoolFactory(caller));

    (Tag tag, int256 accruedAmount) = abi.decode(data, (Tag, int256));

    (int256 amount0, int256 amount1) = INofeeswap(msg.sender).swap(
      conversionPools[tag],
      accruedAmount,
      tag <= address(nofee).tag() ? minX59 : maxX59,
      0x100000000000000000000000000000002,
      ""
    );

    INofeeswap(msg.sender).modifyBalance(
      address(this),
      tag,
      0 - (amount0 > amount1 ? amount0 : amount1)
    );

    int256 nofeeAmount = 0 - (amount0 < amount1 ? amount0 : amount1);

    INofeeswap(msg.sender).take(
      address(nofee),
      address(xNofee),
      uint256(nofeeAmount)
    );

    return abi.encode(nofeeAmount);
  }

  /// @inheritdoc IHook
  function preInitialize(
    bytes calldata hookInput
  ) external override(BaseHook, IHook) onlyNofeeswap returns (bytes4) {
    Tag tag0 = getTag0FromCalldata();
    Tag tag1 = getTag1FromCalldata();
    if (tag0 != address(nofee).tag()) {
      if (tag1 != address(nofee).tag()) {
        revert InvalidTags(tag0, tag1);
      }
    }

    require(
      getPoolIdFromCalldata() & (0x1FFFF << 160) == (0x201 << 160),
      IncompatibleFlags()
    );

    return IHook.preInitialize.selector;
  }

  /// @inheritdoc IHook
  function midSwap(
    bytes calldata hookInput
  ) external override(BaseHook, IHook) onlyNofeeswap returns (bytes4) {
    Tag tag0 = getTag0FromCalldata();
    Tag tag1 = getTag1FromCalldata();
    bool zeroForOne = getZeroForOneFromCalldata();
    if ((tag0 == address(nofee).tag()) == zeroForOne) {
      Tag tag = zeroForOne ? tag1 : tag0;
      if (getPoolIdFromCalldata() == conversionPools[tag]) {
        uint256 nextBlockNumber = lastDisbursed[tag] + delay;
        require(
          nextBlockNumber <= block.number,
          PoolIsClosedForThisDirection(
            getPoolIdFromCalldata(),
            nextBlockNumber,
            block.number
          )
        );
      }
    }

    return IHook.midSwap.selector;
  }

  function _readTags(
    uint256 poolId
  ) private view returns (Tag tag0, Tag tag1) {
    address storageAddress = getStaticParamsStorageAddress(
      address(nofeeswap),
      poolId,
      0
    );
    assembly {
      extcodecopy(storageAddress, 0, 1, 64)
      tag0 := mload(0)
      tag1 := mload(32)
    }
  }
}