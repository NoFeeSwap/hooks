// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {Nofeeswap} from "@core/Nofeeswap.sol";
import {ERC20} from "@openzeppelin/token/ERC20/ERC20.sol";
import {Incentive} from "../Incentive.sol";

/// @title This contract attempts a just in time liquidity attack on the
/// incentive hook.
contract IncentiveWrapper {
  function badCollect(
    address nofeeswap,
    address incentive,
    uint256 tokenId,
    address token0,
    address token1,
    bytes calldata preCollectData,
    bytes calldata postCollectData
  ) public {
    ERC20(token0).approve(incentive, type(uint256).max);
    ERC20(token1).approve(incentive, type(uint256).max);
    Nofeeswap(nofeeswap).setOperator(incentive, true);

    nofeeswap.call(
      abi.encodeWithSelector(
        Nofeeswap.unlock.selector,
        incentive,
        preCollectData
      )
    );
    Incentive(payable(incentive)).collect(tokenId);
    nofeeswap.call(
      abi.encodeWithSelector(
        Nofeeswap.unlock.selector,
        incentive,
        postCollectData
      )
    );
  }
}