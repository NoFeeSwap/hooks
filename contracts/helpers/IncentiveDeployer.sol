// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

/// @title This contract attempts to deploy the incentive contract relay the
/// revert message.
contract IncentiveDeployer {
  function deploy(
    bytes memory code
  ) external returns (
    address incentive
  ) {
    assembly {
      incentive := create(0, add(code, 32), mload(code))
      if eq(incentive, 0) {
        returndatacopy(0, 0, returndatasize())
        revert(0, returndatasize())
      }
    }
  }
}