pragma solidity 0.6.12;

interface IFaiVault {
    function _become(address faiVaultProxy) external;

    function accFTSPerShare() external view returns (uint256);

    function admin() external view returns (address);

    function burnAdmin() external;

    function claim() external;

    function deposit(uint256 _amount) external;

    function fai() external view returns (address);

    function faiVaultImplementation() external view returns (address);

    function fts() external view returns (address);

    function ftsBalance() external view returns (uint256);

    function getAdmin() external view returns (address);

    function pendingAdmin() external view returns (address);

    function pendingFAIVaultImplementation() external view returns (address);

    function pendingFTS(address _user) external view returns (uint256);

    function pendingRewards() external view returns (uint256);

    function setFortressInfo(address _fts, address _fai) external;

    function setNewAdmin(address newAdmin) external;

    function updatePendingRewards() external;

    function userInfo(address) external view returns (uint256 amount, uint256 rewardDebt);

    function withdraw(uint256 _amount) external;
}
