pragma solidity 0.6.12;

//Since fortress renamed from we need to implement its controller funcs
interface FortressComptrollerI {
    // function fortressSpeeds(address ctoken) external view returns (uint256);
    /***  FTS claims ****/
    function claimFortress(address holder) external;

    function enterMarkets(address[] calldata cTokens) external returns (uint256[] memory);

    function getAccountLiquidity(address account)
        external
        view
        returns (
            uint256,
            uint256,
            uint256
        );

    function claimFortress(address holder, address[] memory cTokens) external;

    function faiVaultAddress() external view returns (address);

    function faiController() external view returns (address);

    function mintedFAIs(address) external view returns (uint256);
}
