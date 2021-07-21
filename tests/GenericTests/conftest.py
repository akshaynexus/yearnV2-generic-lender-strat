import pytest
from brownie import Wei, config, Contract


# @pytest.fixture
# def live_strat_usdc_1(Strategy):
#     yield Strategy.at("0xB7e9Bf9De45E1df822E97cA7E0C3D1B62798a4e0")


# @pytest.fixture
# def live_vault_usdc(pm):
#     Vault = pm(config["dependencies"][0]).Vault
#     yield Vault.at("0xD6b53d0f3d4e55fbAaADc140C0B0488293a433f8")


# @pytest.fixture
# def live_GenericCompound_usdc_1(GenericCompound):
#     yield GenericCompound.at("0x33D4c129586562adfd993ebb54E830481F31ef37")


# @pytest.fixture
# def live_GenericCream_usdc_1(GenericCream):
#     yield GenericCream.at("0x1bAaCef951d24c5d70a8cA88D89cE16B37472fB3")


# @pytest.fixture
# def live_GenericDyDx_usdc_1(GenericDyDx):
#     yield GenericDyDx.at("0x6C842746F21Ca34542EDC6895dFfc8D4e7D2bC1c")


# change these fixtures for generic tests
@pytest.fixture
def currency(dai, usdc, weth):
    yield weth


@pytest.fixture
def whale(accounts, web3, weth, gov, chain):
    acc = accounts.at("0xf977814e90da44bfa03b6295a0616a897441acec", force=True)

    # lots of weth account
    wethAcc = accounts.at("0x631Fc1EA2270e98fbD9D92658eCe0F5a269Aa161", force=True)

    weth.transfer(acc, weth.balanceOf(wethAcc), {"from": wethAcc})
    weth.transfer(gov, Wei("100 ether"), {"from": acc})

    assert weth.balanceOf(acc) > 0
    yield acc


@pytest.fixture()
def strategist(accounts, whale, currency):
    decimals = currency.decimals()
    currency.transfer(accounts[1], 100 * (10 ** decimals), {"from": whale})
    yield accounts[1]


@pytest.fixture
def samdev(accounts):
    yield accounts.at("0xC3D6880fD95E06C816cB030fAc45b3ffe3651Cb0", force=True)


@pytest.fixture
def gov(accounts):
    yield accounts[3]


@pytest.fixture
def rewards(gov):
    yield gov  # TODO: Add rewards contract


@pytest.fixture
def guardian(accounts):
    # YFI Whale, probably
    yield accounts[2]


@pytest.fixture
def keeper(accounts):
    # This is our trusty bot!
    yield accounts[4]


@pytest.fixture
def rando(accounts):
    yield accounts[9]


# specific addresses
@pytest.fixture
def usdc(interface):
    yield interface.ERC20("0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d")


@pytest.fixture
def dai(interface):
    yield interface.ERC20("0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3")


@pytest.fixture
def weth(interface):
    yield interface.IWETH("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")


@pytest.fixture
def cdai(interface):
    yield interface.CErc20I("0x5F30fDDdCf14a0997a52fdb7D7F23b93F0f21998")


@pytest.fixture
def cUsdc(interface):
    yield interface.CErc20I("0x3ef88D7FDe18Fe966474FE3878b802F678b029bC")


@pytest.fixture
def crUsdc(interface):
    yield interface.CErc20I("0x3ef88D7FDe18Fe966474FE3878b802F678b029bC")



@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


@pytest.fixture
def vault(gov, rewards, guardian, currency, pm):
    Vault = pm(config["dependencies"][0]).Vault
    vault = Vault.deploy({"from": guardian})
    vault.initialize(currency, gov, rewards, "", "")
    yield vault


@pytest.fixture
def strategy(
    strategist, gov, keeper, vault, BNBFortress, AlphaHomo, Strategy, EthCompound
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)

    bnbFortress = strategist.deploy(BNBFortress, strategy, "Fortress", 3000)
    strategy.addLender(bnbFortress, {"from": gov})

    # alphaHomoPlugin = strategist.deploy(AlphaHomo, strategy, "Alpha Homo")
    # strategy.addLender(alphaHomoPlugin, {"from": gov})

    # compoundPlugin = strategist.deploy(EthCompound, strategy, "Compound")
    # strategy.addLender(compoundPlugin, {"from": gov})

    yield strategy
