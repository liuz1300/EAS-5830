// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");
	mapping( address => address) public underlying_tokens;
	mapping( address => address) public wrapped_tokens;
	address[] public tokens;

	event Creation( address indexed underlying_token, address indexed wrapped_token );
	event Wrap( address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount );
	event Unwrap( address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }

	function createToken(
        address _underlying_token,
        string memory name,
        string memory symbol
    ) public onlyRole(CREATOR_ROLE) returns (address) {
        require(_underlying_token != address(0), "Invalid underlying");
        require(bridgeTokens[_underlying_token] == address(0), "Token already registered");

        // Deploy BridgeToken with bridge contract as admin
        BridgeToken token = new BridgeToken(_underlying_token, name, symbol, address(this));
        bridgeTokens[_underlying_token] = address(token);

        // Grant the bridge contract MINTER_ROLE
        token.grantRole(MINTER_ROLE, address(this));

        emit Creation(_underlying_token, address(token));
        return address(token);
    }

    function wrap(
        address _underlying_token,
        address _recipient,
        uint256 _amount
    ) public onlyRole(WARDEN_ROLE) {
        require(bridgeTokens[_underlying_token] != address(0), "Token not registered");
        require(_recipient != address(0), "Invalid recipient");
        require(_amount > 0, "Amount must be > 0");

        BridgeToken token = BridgeToken(bridgeTokens[_underlying_token]);
        token.mint(_recipient, _amount);

        emit Wrap(_underlying_token, _recipient, _amount);
    }

    function unwrap(
        address _wrapped_token,
        address _recipient,
        uint256 _amount
    ) public {
        require(_wrapped_token != address(0), "Invalid token");
        require(_recipient != address(0), "Invalid recipient");
        require(_amount > 0, "Amount must be > 0");

        BridgeToken token = BridgeToken(_wrapped_token);
        require(token.balanceOf(msg.sender) >= _amount, "Insufficient balance");

        token.burnFrom(msg.sender, _amount);

        emit Unwrap(_wrapped_token, _recipient, _amount);
    }
}
