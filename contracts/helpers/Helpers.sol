// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {Nofeeswap} from "@core/Nofeeswap.sol";
import {NofeeswapDelegatee} from "@core/NofeeswapDelegatee.sol";
import {ERC20FixedSupply} from "@core/helpers/ERC20FixedSupply.sol";
import {Operator} from "@operator/Operator.sol";
import {Deployer} from "@governance/Deployer.sol";

contract NofeeswapHelper is Nofeeswap {
  constructor(
    address delegatee,
    address admin
  ) Nofeeswap(delegatee, admin) {}
}
contract NofeeswapDelegateeHelper is NofeeswapDelegatee {
  constructor(address nofeeswap) NofeeswapDelegatee(nofeeswap) {}
}
contract ERC20FixedSupplyHelper is ERC20FixedSupply {
  constructor(
    string memory name,
    string memory symbol,
    uint256 initialSupply,
    address owner
  ) ERC20FixedSupply(name, symbol, initialSupply, owner) {}
}
contract OperatorHelper is Operator {
  constructor(
    address _nofeeswap,
    address _permit2,
    address _weth9,
    address _quoter
  ) Operator(_nofeeswap, _permit2, _weth9, _quoter) {}
}
contract DeployerHelper is Deployer {
  constructor(address admin) Deployer(admin) {}
}