import json
import random
import asyncio
import time
from web3 import AsyncWeb3
from web3.providers.async_rpc import AsyncHTTPProvider
from eth_utils import to_bytes
from termcolor import colored
from loguru import logger


'''
    Bridge agEUR on https://app.angle.money/ 
    chains : Gnosis | Celo | Arbitrum | Polygon | Bsc
'''

from_chain_name = "Gnosis"    # Enter here the network from which you're bridging
to_chain_name = "Celo"        # Enter here the network to which you're bridging
delay_range = (10, 20)        # Enter here your delay range between wallets
random_wallets = True         # Enter True here if you want to select random wallets
max_attempts = 1              # Enter number of maximum attempts for transaction execution

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
            '0x4b1E2c2762667331Bc91648052F646d1b0d35984',  # agEUR contract
            145,  # Chain ID LZ
            'https://gnosisscan.io'  # explorer
        )


class Celo(Chain):
    def __init__(self):
        super().__init__(
            'https://rpc.ankr.com/celo',  # rpc
            '0xf1dDcACA7D17f8030Ab2eb54f2D9811365EFe123',  # bridge contract
            '0xC16B81Af351BA9e64C1a069E3Ab18c244A1E3049',  # agEUR contract
            125,  # Chain ID LZ
            'https://celoscan.io'  # explorer
        )


class Arbitrum(Chain):
    def __init__(self):
        super().__init__(
            'https://rpc.ankr.com/arbitrum',  # rpc
            '0x16cd38b1B54E7abf307Cb2697E2D9321e843d5AA',  # bridge contract
            '0xFA5Ed56A203466CbBC2430a43c66b9D8723528E7',  # agEUR contract
            110,  # Chain ID LZ
            'https://arbiscan.io'  # explorer
        )


class Bsc(Chain):
    def __init__(self):
        super().__init__(
            'https://rpc.ankr.com/bsc',  # rpc
            '0xe9f183FC656656f1F17af1F2b0dF79b8fF9ad8eD',  # bridge contract
            '0x12f31B73D812C6Bb0d735a218c086d44D5fe5f89',  # agEUR contract
            102,  # Chain ID LZ
            'https://bscscan.com'  # explorer
        )


class Polygon(Chain):
    def __init__(self):
        super().__init__(
            'https://rpc.ankr.com/polygon',  # rpc
            '0x0c1EBBb61374dA1a8C57cB6681bF27178360d36F',  # bridge contract
            '0xE0B52e49357Fd4DAf2c15e02058DCE6BC0057db4',  # agEUR contract
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

    def select_chains(self, from_chain_name, to_chain_name):
        from_chain = self.get_chain(from_chain_name)
        to_chain = self.get_chain(to_chain_name)

        if from_chain is None or to_chain is None:
            raise ValueError(
                "Wrong network name")

        return from_chain, to_chain


async def approve_ag_eur(chain_from, wallet, max_attempts):
    try:
        account = chain_from.w3.eth.account.from_key(wallet)
        address = account.address
        balance = await check_balance(address, chain_from.ag_eur_contract)
        allowance = await chain_from.ag_eur_contract.functions.allowance(address, chain_from.bridge_address).call()

        if balance < allowance:
            return

        for attempt in range(1, max_attempts+1):
            try:

                nonce = await chain_from.w3.eth.get_transaction_count(address)

                if chain_from.chain_id == 102:  # Binance Smart Chain
                    gas_price = chain_from.w3.to_wei(2, 'gwei')
                else:
                    gas_price = await chain_from.w3.eth.gas_price

                max_amount = chain_from.w3.to_wei(2 ** 64 - 1, 'ether')
                approve_txn = await chain_from.ag_eur_contract.functions.approve(
                    chain_from.bridge_address, max_amount
                ).build_transaction({
                    'from': address,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                })

                gasLimit = await chain_from.w3.eth.estimate_gas(approve_txn)
                approve_txn['gas'] = int(gasLimit * random.uniform(1.2, 1.3))

                signed_approve_txn = chain_from.w3.eth.account.sign_transaction(
                    approve_txn, wallet)
                raw_approve_txn_hash = await chain_from.w3.eth.send_raw_transaction(signed_approve_txn.rawTransaction)
                approve_txn_hash = chain_from.w3.to_hex(
                    raw_approve_txn_hash)
                receipt = await chain_from.w3.eth.wait_for_transaction_receipt(approve_txn_hash)

                if receipt['status'] == 1:
                    logger.success(
                        f"{chain_from.__class__.__name__} | agEUR approval sent | Tx: {chain_from.blockExplorerUrl}/tx/{approve_txn_hash}")
                    await asyncio.sleep(random.randint(5, 10))
                    return

            except Exception as error:
                logger.error(
                    f"Error occurred during transaction: {str(error)}")

            logger.warning(f"Attempt {attempt} failed. Retrying...")
            await asyncio.sleep(random.randint(5, 10))

            logger.error(
                f"Reached maximum number of attempts. Failed to send agEUR approval.")

    except Exception as error:
        logger.error(f'{error}')


async def bridge_ag_eur(chain_from, chain_to, wallet, max_attempts):
    try:
        account = chain_from.w3.eth.account.from_key(wallet)
        address = account.address
        balance = await check_balance(address, chain_from.ag_eur_contract)
        address_edited = to_bytes(hexstr=account.address)

        for attempt in range(1, max_attempts+1):
            try:
                nonce = await chain_from.w3.eth.get_transaction_count(address)
                if chain_from.chain_id == 102:  # Binance Smart Chain
                    gas_price = chain_from.w3.to_wei(2, 'gwei')
                else:
                    gas_price = await chain_from.w3.eth.gas_price
                    
                adapter_params = '0x00010000000000000000000000000000000000000000000000000000000000030d40'
                zroPaymentAddress = '0x' + '0' * 40

                fees = await chain_from.bridge_contract.functions.estimateSendFee(
                    chain_to.chain_id,
                    address_edited,
                    balance,
                    True,
                    adapter_params
                ).call()

                fee = fees[0]

                bridge_txn = await chain_from.bridge_contract.functions.send(
                    chain_to.chain_id, address_edited, balance, address, zroPaymentAddress, adapter_params
                ).build_transaction({
                    'from': address,
                    'value': fee,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                })

                gasLimit = await chain_from.w3.eth.estimate_gas(bridge_txn)
                bridge_txn['gas'] = int(gasLimit * random.uniform(1.2, 1.3))

                signed_bridge_txn = chain_from.w3.eth.account.sign_transaction(
                    bridge_txn, wallet)
                raw_bridge_txn_hash = await chain_from.w3.eth.send_raw_transaction(signed_bridge_txn.rawTransaction)
                bridge_txn_hash = chain_from.w3.to_hex(raw_bridge_txn_hash)
                receipt = await chain_from.w3.eth.wait_for_transaction_receipt(bridge_txn_hash)

                if receipt['status'] == 1:
                    token_amount = balance / 10**18
                    logger.success(
                        f"{chain_from.__class__.__name__} | Bridge tx sent | Token Amount: {token_amount} | Tx: {chain_from.blockExplorerUrl}/tx/{bridge_txn_hash}")
                    return

            except Exception as e:
                logger.error(f"Error occurred during transaction: {str(e)}")

            logger.warning(f"Attempt {attempt} failed. Retrying...")
            await asyncio.sleep(random.randint(5, 10))

        logger.error(
            f"Reached maximum number of attempts. Failed to send bridge tx.")

    except Exception as e:
        logger.error(f"Error occurred during transaction: {str(e)}")

    await asyncio.sleep(random.randint(5, 10))


async def check_balance(address, contract):
    balance = await contract.functions.balanceOf(address).call()
    return balance


async def work(wallet, from_chain, to_chain, max_attempts):
    account = from_chain.w3.eth.account.from_key(wallet)
    address = account.address
    chains = [(from_chain, to_chain, from_chain.ag_eur_contract, bridge_ag_eur)]

    for (from_chain, to_chain, contract, bridge_fn) in chains:
        balance = await check_balance(address, contract)
        if balance < 10000000000000000:
            logger.error(f'Wallet: {address} | Insufficient balance')
            continue

        try:
            await approve_ag_eur(from_chain, wallet, max_attempts)
            await bridge_fn(from_chain, to_chain, wallet, max_attempts)
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
    from_chain, to_chain = chain_selector.select_chains(
        from_chain_name, to_chain_name)

    if random_wallets:
        random.shuffle(WALLETS)

    for wallet_index, wallet in enumerate(WALLETS, start=1):
        account = from_chain.w3.eth.account.from_key(wallet)
        address = account.address

        print(f"{wallet_index}/{total_wallets} : {address}")
        print()
        tx_str = f'Angle_bridge : {from_chain_name} => {to_chain_name}'
        logger.info(tx_str)
        logger.info("Starting bridge...")

        await work(wallet, from_chain, to_chain, max_attempts)

    logger.info(colored(f'All done', 'green'))


if __name__ == '__main__':
    asyncio.run(main())

