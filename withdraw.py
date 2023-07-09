import json
import random
import asyncio
import time
from web3 import AsyncWeb3
from web3.providers.async_rpc import AsyncHTTPProvider
from termcolor import colored
from loguru import logger


'''
    Withdraw LZ-agEUR 
    chains : Gnosis | Celo | Arbitrum | Polygon | Bsc
'''

from_chain_name = "Celo"    # Enter here the network from which you're bridging
delay_range = (20, 60)      # Enter here your delay range between wallets
random_wallets = True       # Enter True here if you want to select random wallets


with open('router_abi.json') as f:
    router_abi = json.load(f)
with open('ag_eur_abi.json') as f:
    ag_eur_abi = json.load(f)


class Chain():
    def __init__(self, rpc_url, bridge_address, ag_eur_address, chainId, blockExplorerUrl):
        self.w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.bridge_address = self.w3.to_checksum_address(bridge_address)
        self.bridge_contract = self.w3.eth.contract(
            address=self.bridge_address, abi=router_abi)
        self.ag_eur_address = self.w3.to_checksum_address(ag_eur_address)
        self.ag_eur_contract = self.w3.eth.contract(
            address=self.ag_eur_address, abi=ag_eur_abi)
        self.chain_id = chainId
        self.blockExplorerUrl = blockExplorerUrl


class Gnosis(Chain):
    def __init__(self):
        super().__init__(
            'https://rpc.ankr.com/gnosis',  # rpc
            '0xFA5Ed56A203466CbBC2430a43c66b9D8723528E7',  # bridge contract
            '0xFA5Ed56A203466CbBC2430a43c66b9D8723528E7',  # agEUR contract
            145,  # Chain ID LZ
            'https://gnosisscan.io'  # explorer
        )


class Celo(Chain):
    def __init__(self):
        super().__init__(
            'https://rpc.ankr.com/celo',  # rpc
            '0xf1dDcACA7D17f8030Ab2eb54f2D9811365EFe123',  # bridge contract
            '0xf1dDcACA7D17f8030Ab2eb54f2D9811365EFe123',  # agEUR contract
            125,  # Chain ID LZ
            'https://celoscan.io'  # explorer
        )


class Arbitrum(Chain):
    def __init__(self):
        super().__init__(
            'https://rpc.ankr.com/arbitrum',  # rpc
            '0x16cd38b1B54E7abf307Cb2697E2D9321e843d5AA',  # bridge contract
            '0x16cd38b1B54E7abf307Cb2697E2D9321e843d5AA',  # agEUR contract
            110,  # Chain ID LZ
            'https://arbiscan.io'  # explorer
        )


class Bsc(Chain):
    def __init__(self):
        super().__init__(
            'https://rpc.ankr.com/bsc',  # rpc
            '0xe9f183FC656656f1F17af1F2b0dF79b8fF9ad8eD',  # bridge contract
            '0xe9f183FC656656f1F17af1F2b0dF79b8fF9ad8eD',  # agEUR contract
            102,  # Chain ID LZ
            'https://bscscan.com'  # explorer
        )


class Polygon(Chain):
    def __init__(self):
        super().__init__(
            'https://rpc.ankr.com/arbitrum',  # rpc
            '0x0c1EBBb61374dA1a8C57cB6681bF27178360d36F',  # bridge contract
            '0x0c1EBBb61374dA1a8C57cB6681bF27178360d36F',  # agEUR contract
            109,  # Chain ID LZ
            'https://polygonscan.com'  # explorer
        )


class ChainSelector:
    def __init__(self):
        self.chains = {
            "Gnosis": Gnosis(),
            "Celo": Celo(),
            "Arbitrum": Arbitrum(),
            "Bsc": Bsc(),
            "Polygon": Polygon()
        }

    def get_chain(self, chain_name):
        return self.chains.get(chain_name)

    def select_chains(self, from_chain_name):
        from_chain = self.get_chain(from_chain_name)

        if from_chain is None:
            raise ValueError(
                "Wrong network name")

        return from_chain


async def withdraw_LZ_agEUR(chain_from, wallet):
    try:

        account = chain_from.w3.eth.account.from_key(wallet)
        address = account.address
        balance = await check_balance(address, chain_from.ag_eur_contract)

        if balance:
            refund_address = account.address
            amountIn = balance

            swap_txn = await chain_from.bridge_contract.functions.withdraw(amountIn, refund_address
            ).build_transaction({
                'from': address,
                'value': 0,
                'gasPrice': await chain_from.w3.eth.gas_price,
                'nonce': await chain_from.w3.eth.get_transaction_count(address),
            })

            signed_swap_txn = chain_from.w3.eth.account.sign_transaction(swap_txn, wallet)
            swap_txn_hash = await chain_from.w3.eth.send_raw_transaction(signed_swap_txn.rawTransaction)

            return swap_txn_hash
        else:
            print(f"Withdraw was failed {wallet} with {balance}")
    except Exception as e:
        print(f" Fail Exception occurred in withdraw LZ_agEUR: {wallet} | {e}")


async def check_balance(address, contract):
    balance = await contract.functions.balanceOf(address).call()
    return balance


async def work(wallet, from_chain):
    account = from_chain.w3.eth.account.from_key(wallet)
    address = account.address
    chains = [(from_chain, from_chain.ag_eur_contract, withdraw_LZ_agEUR)]

    for (from_chain, contract, swap_fn) in chains:
        try:
            await swap_fn(from_chain, wallet)
        except Exception as e:
            logger.error(f"Error occurred during transaction: {str(e)}")

    logger.info(f'Wallet: {address} | done')

    delay = random.randint(*delay_range)
    logger.info(f"Waiting for {delay} seconds before the next wallet...")
    for i in range(1, delay + 1):
        time.sleep(1)
        print(f"\rsleep : {i}/{delay}", end="")
    print()
    print()
    print()


async def main():
    with open('wallets.txt', 'r') as f:
        WALLETS = [row.strip() for row in f]

    total_wallets = len(WALLETS)

    chain_selector = ChainSelector()
    from_chain = chain_selector.select_chains(
        from_chain_name)

    if random_wallets:
        random.shuffle(WALLETS)

    for wallet_index, wallet in enumerate(WALLETS, start=1):
        account = from_chain.w3.eth.account.from_key(wallet)
        address = account.address

        print(f"{wallet_index}/{total_wallets} : {address}")
        print()
        tx_str = f'Withdraw_LZ-agEUR : {from_chain_name}'
        logger.info(tx_str)
        logger.info("Starting withdraw...")

        await work(wallet, from_chain)

    logger.info(colored(f'All done', 'green'))


if __name__ == '__main__':
    asyncio.run(main())
