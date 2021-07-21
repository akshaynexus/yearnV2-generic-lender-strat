from itertools import count
from brownie import Wei, reverts, BNBFortress, chain
from useful_methods import genericStateOfStrat, genericStateOfVault, deposit, sleep
import random
import brownie


def test_donations(strategy, web3, chain, vault, currency, whale, strategist, gov):
    deposit_limit = Wei("1000 ether")
    vault.setDepositLimit(deposit_limit, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 50, {"from": gov})

    amount = Wei("50 ether")
    deposit(amount, gov, currency, vault)
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
    harvest_strat(strategy, gov)
    assert vault.strategies(strategy).dict()["totalGain"] == 0

    donation = Wei("1 ether")

    # donation to strategy
    currency.transfer(strategy, donation, {"from": whale})
    assert vault.strategies(strategy).dict()["totalGain"] == 0
    harvest_strat(strategy, gov)
    chain.sleep(6000)
    chain.mine(1)
    donationWithFees = donation - (donation *0.01)
    assert vault.strategies(strategy).dict()["totalGain"] >= donationWithFees
    assert currency.balanceOf(vault) >= donationWithFees

    harvest_strat(strategy, gov)
    assert vault.strategies(strategy).dict()["totalDebt"] >= donationWithFees + amount

    # donation to vault
    currency.transfer(vault, donation, {"from": whale})
    assert (
        vault.strategies(strategy).dict()["totalGain"] >= donationWithFees
        and vault.strategies(strategy).dict()["totalGain"] < donationWithFees * 2
    )
    harvest_strat(strategy, gov)
    assert vault.strategies(strategy).dict()["totalDebt"] >= donationWithFees * 2 + amount
    harvest_strat(strategy, gov)

    assert (
        vault.strategies(strategy).dict()["totalGain"] >= donationWithFees
        and vault.strategies(strategy).dict()["totalGain"] < donationWithFees * 2
    )
    # check share price is close to expected
    assert (
        vault.pricePerShare() > ((donationWithFees * 2 + amount) / amount) * 0.95 * 1e18
        and vault.pricePerShare() < ((donationWithFees * 2 + amount) / amount) * 1.05 * 1e18
    )


def test_good_migration(
    strategy, chain, Strategy, web3, vault, currency, whale, rando, gov, strategist
):
    # Call this once to seed the strategy with debt
    deposit_limit = Wei("1000 ether")
    vault.setDepositLimit(deposit_limit, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 50, {"from": gov})

    amount1 = Wei("500 ether")
    deposit(amount1, whale, currency, vault)

    amount1 = Wei("50 ether")
    deposit(amount1, gov, currency, vault)

    harvest_strat(strategy, gov)
    sleep(chain, 10)
    harvest_strat(strategy, gov)

    strategy_debt = vault.strategies(strategy).dict()["totalDebt"]
    prior_position = strategy.estimatedTotalAssets()
    assert strategy_debt > 0

    new_strategy = strategist.deploy(Strategy, vault)
    assert vault.strategies(new_strategy).dict()["totalDebt"] == 0
    assert currency.balanceOf(new_strategy) == 0

    # Only Governance can migrate
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": rando})

    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
    assert vault.strategies(new_strategy).dict()["totalDebt"] == strategy_debt
    assert (
        new_strategy.estimatedTotalAssets() > prior_position * 0.999
        or new_strategy.estimatedTotalAssets() < prior_position * 1.001
    )


def test_vault_shares_generic(
    strategy, web3, chain, vault, currency, whale, strategist, gov
):
    deposit_limit = Wei("1000 ether")
    # set limit to the vault
    vault.setDepositLimit(deposit_limit, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})
    print(currency)

    assert vault.totalSupply() == 0
    amount1 = Wei("50 ether")
    deposit(amount1, whale, currency, vault)
    whale_share = vault.balanceOf(whale)
    deposit(amount1, gov, currency, vault)
    gov_share = vault.balanceOf(gov)

    assert gov_share == whale_share
    assert vault.pricePerShare() == 1e18
    assert vault.pricePerShare() * whale_share / 1e18 == amount1

    assert vault.pricePerShare() * whale_share / 1e18 == vault.totalAssets() / 2
    assert gov_share == whale_share

    harvest_strat(strategy, gov)
    # sleepAndHarvest(5, vault, strategy, gov)
    harvest_strat(strategy, gov)
    # no profit yet
    whale_share = vault.balanceOf(whale)
    gov_share = vault.balanceOf(gov)
    assert gov_share == whale_share

    sleep(chain, 100)
    whale_share = vault.balanceOf(whale)
    gov_share = vault.balanceOf(gov)
    # no profit just aum fee. meaning total balance should be the same
    assert (gov_share + whale_share) * vault.pricePerShare() / 1e18 >= 100 * 1e18

    whale_share = vault.balanceOf(whale)
    gov_share = vault.balanceOf(gov)
    # add strategy return
    assert vault.totalSupply() == whale_share + gov_share
    value = (gov_share + whale_share) * vault.pricePerShare() / 1e18
    assert (
        value * 0.99999 < vault.totalAssets() and value * 1.00001 > vault.totalAssets()
    )
    # check we are within 0.1% of expected returns
    assert (
        value < strategy.estimatedTotalAssets() * 1.001
        and value > strategy.estimatedTotalAssets() * 0.999
    )
    sleepAndHarvest(4, vault, strategy, gov)

    assert gov_share > whale_share


def test_vault_emergency_exit_generic(
    strategy, web3, chain, vault, currency, whale, strategist, gov
):
    deposit_limit = Wei("1000000 ether")
    vault.setDepositLimit(deposit_limit, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 50, {"from": gov})

    amount0 = Wei("500 ether")
    deposit(amount0, whale, currency, vault)

    amount1 = Wei("50 ether")
    deposit(amount1, gov, currency, vault)

    harvest_strat(strategy, gov)
    sleep(chain, 30)

    assert vault.emergencyShutdown() == False
    vault.setEmergencyShutdown(True, {"from": gov})
    assert vault.emergencyShutdown()

    ## emergency shutdown
    harvest_strat(strategy, gov)
    harvest_strat(strategy, gov)
    assert currency.balanceOf(vault) > amount0 + amount1
    assert strategy.estimatedTotalAssets() < Wei("0.01 ether")

    # Restore power
    vault.setEmergencyShutdown(False, {"from": gov})
    harvest_strat(strategy, gov)
    assert strategy.estimatedTotalAssets() > amount0 + amount1
    assert currency.balanceOf(vault) == 0

    # Withdraw All
    vault.withdraw(vault.balanceOf(gov), {"from": gov})


def test_strat_emergency_exit_generic(
    strategy, web3, chain, vault, currency, whale, strategist, gov
):

    deposit_limit = Wei("1000000 ether")
    vault.setDepositLimit(deposit_limit, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 50, {"from": gov})

    amount0 = Wei("500 ether")
    deposit(amount0, whale, currency, vault)

    amount1 = Wei("50 ether")
    deposit(amount1, gov, currency, vault)

    harvest_strat(strategy, gov)
    sleep(chain, 30)

    assert strategy.emergencyExit() == False

    strategy.setEmergencyExit({"from": gov})
    assert strategy.emergencyExit()

    ## emergency shutdown
    harvest_strat(strategy, gov)
    assert currency.balanceOf(vault) >= amount0 + amount1

    # Withdraw All
    vault.withdraw(vault.balanceOf(gov), {"from": gov})


def test_strat_graceful_exit_generic(
    strategy, web3, chain, vault, currency, whale, strategist, gov
):

    deposit_limit = Wei("1000000 ether")
    vault.setDepositLimit(deposit_limit, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 50, {"from": gov})

    amount0 = Wei("500 ether")
    deposit(amount0, whale, currency, vault)

    amount1 = Wei("50 ether")
    deposit(amount1, gov, currency, vault)

    harvest_strat(strategy, gov)
    sleep(chain, 30)

    vault.revokeStrategy(strategy, {"from": gov})

    ## emergency shutdown
    harvest_strat(strategy, gov)
    harvest_strat(strategy, gov)
    assert currency.balanceOf(vault) >= amount0 + amount1


def test_apr_generic(strategy, web3, chain, vault, currency, whale, strategist, gov):

    deposit_limit = Wei("1000000 ether")
    vault.setDepositLimit(deposit_limit, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 50, {"from": gov})

    deposit_amount = Wei("1000 ether")
    deposit(deposit_amount, whale, currency, vault)

    # invest
    harvest_strat(strategy, gov)

    startingBalance = vault.totalAssets()

    for i in range(2):
        waitBlock = 25
        print(f"\n----wait {waitBlock} blocks----")
        sleep(chain, waitBlock)
        strategy.harvest({"from": strategist})

        profit = (vault.totalAssets() - startingBalance).to("ether")
        strState = vault.strategies(strategy).dict()
        totalReturns = strState["totalGain"]
        totaleth = totalReturns.to("ether")
        difff = profit - totaleth

        blocks_per_year = 2_300_000
        assert startingBalance != 0
        time = (i + 1) * waitBlock
        assert time != 0
        apr = (totalReturns / startingBalance) * (blocks_per_year / time)
        print(apr)
        print(f"implied apr: {apr:.8%}")

    vault.withdraw(vault.balanceOf(whale), {"from": whale})

def harvest_strat(strat,caller):
    fortressStrat = BNBFortress.at(strat.lenders(0))
    strat.harvest({"from": caller})

def sleepAndHarvest(times,vault, strat, gov):
    fortressStrat = BNBFortress.at(strat.lenders(0))

    for i in range(times):
        # debugStratData(strat, "Before harvest" + str(i))
        # Alchemix staking pools calculate reward per block,so mimic mainnet chain flow to get accurate returns
        for j in range(7200):
            chain.sleep(3)
            chain.mine(1)
        fortressStrat.harvest({"from": gov})
        fortressStrat.deposit({"from": gov})
        strat.harvest({"from": gov})
        debugStratData(strat,vault, "After harvest" + str(i))


# Used to debug strategy balance data
def debugStratData(strategy,vault, msg):
    print(msg)
    print("Total assets " + str(strategy.estimatedTotalAssets()))
    print("PPS " + str(vault.pricePerShare() / 1e18))

    # print("want Balance " + str(strategy.balanceOfWant()))
    # print("Stake balance " + str(strategy.balanceOfStake()))
    # print("Pending reward " + str(strategy.pendingReward()))