<h1 align="center">Angle bridge </h1>
  
This script is designed to automate bridging of agEUR across different chains using Angle Protocol - https://app.angle.money. The supported chains are Gnosis, Celo, Arbitrum, Bsc and Polygon.


<h2>Setup</h2>

1. Install the necessary dependencies using `pip3` for Mac or `pip` for Windows
2. Prepare your wallets. You will need to provide the private keys of the wallets to be used in a file named `wallets.txt`. Each line of the file should contain one private key.


<h2>Usage</h2>

Configurate scripts in a file `main.py`.

- from_chain_name: The name of the chain you are bridging from. Can be "Gnosis", "Celo", "Arbitrum", "Bsc" or "Polygon".
- to_chain_name: The name of the chain you are bridging to. Can be "Gnosis", "Celo", "Arbitrum", "Bsc" or "Polygon".
- delay_range: A tuple that defines the minimum and maximum delay (in seconds) between transactions for different wallets.
- random_wallets: If set to True, the script will randomly shuffle the wallets before starting.
- max_attempts: Number of attempts when a transaction fails 

Once you have prepared your setup and configured the script, you can run it using:

For Windows: <pre><code>python main.py</code></pre>
For Mac: <pre><code>python3 main.py</code></pre>


<h2>Details</h2>

Before you start, check the bridge limits https://app.angle.money/bridges-agEUR. If you received lz-agEUR, read this - https://docs.angle.money/overview/guides/bridge and you can use `withdraw.py`


The script will iterate over each wallet in `wallets.txt`. For each wallet, it will approve the maximum possible amount of agEUR for the bridge contract, then bridge the entire balance of the wallet to the destination chain. It will wait for a random amount of time (within the delay_range) before moving on to the next wallet.

The script also contains logging functionality that will provide detailed information about each transaction.

<h2></h2>
Please note that handling private keys is sensitive and you should be very careful not to leak them. Never share your private keys with anyone you do not trust completely. Use this script at your own risk. DYOR
