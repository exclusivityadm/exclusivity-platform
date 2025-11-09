// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract LUXToken is ERC20, Ownable {
    mapping(address => bool) public minters;

    error TransfersDisabled();
    error NotMinter();

    constructor(string memory name_, string memory symbol_, address owner_)
        ERC20(name_, symbol_) Ownable(owner_) {}

    modifier onlyMinter() {
        if (!minters[msg.sender] && msg.sender != owner()) revert NotMinter();
        _;
    }

    function setMinter(address who, bool allowed) external onlyOwner {
        minters[who] = allowed;
    }

    function mint(address to, uint256 amount) external onlyMinter {
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external onlyMinter {
        _burn(from, amount);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            revert TransfersDisabled();
        }
        super._update(from, to, value);
    }
}
