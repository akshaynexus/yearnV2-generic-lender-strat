pragma solidity 0.6.12;

interface IFaiController {
    function _become(address unitroller) external;

    function _initializeFortressFAIState(uint256 blockNumber) external returns (uint256);

    function _setComptroller(address comptroller_) external returns (uint256);

    function admin() external view returns (address);

    function calcDistributeFAIMinterFortress(address faiMinter)
        external
        returns (
            uint256,
            uint256,
            uint256,
            uint256
        );

    function comptroller() external view returns (address);

    function faiControllerImplementation() external view returns (address);

    function fortressFAIMinterIndex(address) external view returns (uint256);

    function fortressFAIState() external view returns (uint224 index, uint32 _block);

    function fortressInitialIndex() external view returns (uint224);

    function getBlockNumber() external view returns (uint256);

    function getFAIAddress() external view returns (address);

    function getMintableFAI(address minter) external view returns (uint256, uint256);

    function isFortressFAIInitialized() external view returns (bool);

    function mintFAI(uint256 mintFAIAmount) external returns (uint256);

    function pendingAdmin() external view returns (address);

    function pendingFAIControllerImplementation() external view returns (address);

    function repayFAI(uint256 repayFAIAmount) external returns (uint256);

    function updateFortressFAIMintIndex() external returns (uint256);
}
