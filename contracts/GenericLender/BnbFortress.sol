pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "./EthCream.sol";
import "../interfaces/Fortress/FortressComptrollerI.sol";
import "../interfaces/Fortress/IFaiController.sol";
import "../interfaces/Fortress/IFaiVault.sol";
import "../Interfaces/UniswapInterfaces/IUniswapV2Router02.sol";

contract BNBFortress is EthCream {
    fallback() external payable {}

    //Init all the interfaces to fortress
    FortressComptrollerI public constant comptroller = FortressComptrollerI(0x67340Bd16ee5649A37015138B3393Eb5ad17c195);
    IFaiController public faiController = IFaiController(comptroller.faiController());
    IFaiVault public faiVault = IFaiVault(comptroller.faiVaultAddress());

    address public constant router = 0xBe65b8f75B9F20f4C522e0067a3887FADa714800;
    address public constant fts = 0x4437743ac02957068995c48E08465E0EE1769fBE;
    address public constant wbnb = 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c;

    IERC20 iFAI = IERC20(faiController.getFAIAddress());
    IERC20 iFTS = IERC20(fts);

    //Raised to 10000,100% = 10000,lower amount minted for volatile tokens
    //90% Ratio recommeneded for stables,40% or lower for other non-stable
    uint256 public FAIMintRatio;

    uint256 DIVISOR = 10000;
    event RatioWithdrawn(uint256 ratio);

    constructor(
        address _strategy,
        string memory name,
        uint256 _mintRatio
    ) public EthCream(_strategy, name) {
        _initializeFaiSpecifics(_mintRatio);
    }

    function _initializeFaiSpecifics(uint256 _mintRatio) internal {
        //Fortress
        crETH = CEtherI(0xE24146585E882B6b59ca9bFaaaFfED201E4E5491);
        weth = IWETH(wbnb);
        //Enable markets to borrow with ctoken
        address[] memory collaterals = new address[](1);
        collaterals[0] = address(crETH);
        comptroller.enterMarkets(collaterals);
        //Approve vault to spend fai
        iFAI.safeApprove(comptroller.faiVaultAddress(), type(uint256).max);
        //Approve fai controller to repay fai debt
        iFAI.safeApprove(comptroller.faiController(), type(uint256).max);
        iFTS.safeApprove(router, type(uint256).max);
        require(_mintRatio <= 10000, "Max");
        FAIMintRatio = _mintRatio;
    }

    function updateFaiRatio(uint256 _newRatio) external management {
        require(_newRatio <= 10000, "Max");
        FAIMintRatio = _newRatio;
    }

    function _withdraw(uint256 amount) internal virtual override returns (uint256) {
        _disposeOfComp();
        rebalanceFai();
        //Calculate how much fai we have to withdraw to maintain target debt ratio
        (, uint256 mintedFais) = getLivePosition();
        uint256 curBal = underlyingBalanceStored();
        //Decrease = Original Number - New Number
        uint256 ratioBeingWithdrawn = curBal > amount ? DIVISOR - (((curBal - amount) * DIVISOR) / curBal) : DIVISOR;
        emit RatioWithdrawn(ratioBeingWithdrawn);
        uint256 faiToRepay = curBal.mul(ratioBeingWithdrawn).div(DIVISOR);
        unstakeAndRepayFai(faiToRepay);
        super._withdraw(amount);
    }

    function withdrawAll() public virtual override management returns (bool all) {
        _disposeOfComp();
        rebalanceFai();
        (, uint256 mintedFais) = getLivePosition();
        unstakeAndRepayFai(mintedFais);
        all = super.withdrawAll();
    }

    function deposit() public override management {
        _disposeOfComp();
        rebalanceFai();
        super.deposit();
        //Mint and deposit FAI to vault
        mintAndStakeFai();
    }

    function unstakeAndRepayFaiManage(uint256 amount) external management {
        unstakeAndRepayFai(amount);
    }

    //Calculate how much we need to unstake to withdraw our required balance
    function unstakeAndRepayFai(uint256 amount) internal {
        //Unstake the amount
        faiVault.withdraw(amount);
        //Repay the fai
        faiController.repayFAI(amount);
    }

    function getLivePosition() public view returns (uint256 deposits, uint256 borrows) {
        (, deposits, ) = comptroller.getAccountLiquidity(address(this));

        borrows = comptroller.mintedFAIs(address(this));
    }

    function calculateAvailableFai() external view returns (uint256) {
        //First get total mintable
        (, uint256 mintable) = faiController.getMintableFAI(address(this));
        return mintable.mul(FAIMintRatio).div(DIVISOR);
    }

    //WARNING. manipulatable and simple routing. Only use for safe functions
    function priceCheck(
        address start,
        address end,
        uint256 _amount
    ) public view returns (uint256) {
        if (_amount == 0) {
            return 0;
        }
        address[] memory path;
        if (start == wbnb) {
            path = new address[](2);
            path[0] = wbnb;
            path[1] = end;
        } else {
            path = new address[](3);
            path[0] = start;
            path[1] = wbnb;
            path[2] = end;
        }

        uint256[] memory amounts = IUniswapV2Router02(router).getAmountsOut(_amount, path);

        return amounts[amounts.length - 1];
    }

    function claimComp() public {
        //First claim incentives for lending
        address[] memory tokens = new address[](1);
        tokens[0] = address(crETH);

        comptroller.claimFortress(address(this), tokens);
        //Then claim the fts rewards from deposit and minting FAI
        faiVault.claim();
    }

    //sell fts function
    function _disposeOfComp() internal {
        uint256 _comp = IERC20(fts).balanceOf(address(this));
        if (_comp > 10 wei) {
            address[] memory path = new address[](2);
            path[0] = fts;
            path[1] = wbnb;
            IUniswapV2Router02(router).swapExactTokensForTokens(_comp, uint256(0), path, address(this), now);
        }
    }

    function harvest() external {
        rebalanceFai();
        //claim fts accrued
        claimComp();
        //sell fts
        _disposeOfComp();
        //Deposit proceeds back in
        deposit();
    }

    function rebalanceFai() public {
        if (this.hasAssets()) {
            (uint256 depositWorth, uint256 mintedFais) = getLivePosition();
            (, uint256 mintable) = faiController.getMintableFAI(address(this));
            uint256 totalFaiM = mintable + mintedFais;
            uint256 totalMax = depositWorth / 2;
            uint256 ratioMax = mintable.mul(FAIMintRatio).div(DIVISOR);
            //Get difference between ratio ,unstake and repay that amount
            uint256 extraFromRatio = mintedFais > ratioMax ? mintedFais - ratioMax : 0;
            if (extraFromRatio > 0) unstakeAndRepayFai(extraFromRatio);
        }
    }

    function mintAndStakeFai() internal {
        //Get how much is mintable,get ratio,minus from already minted fai
        faiController.mintFAI(this.calculateAvailableFai());
        faiVault.deposit(iFAI.balanceOf(address(this)));
    }

    function claimAndSendFAi() public management {
        claimComp();
        iFAI.transfer(msg.sender, iFAI.balanceOf(address(this)));
    }
}
