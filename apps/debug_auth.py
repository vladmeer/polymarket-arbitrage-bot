
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from src.bot import TradingBot
from src.config import Config
from src.signer import OrderSigner
from src.client import ClobClient, ApiError

def test_auth():
    print("--- Testing Authentication ---")
    
    private_key = os.environ.get("POLY_PRIVATE_KEY")
    if not private_key:
        print("Error: POLY_PRIVATE_KEY not found in .env")
        return

    try:
        signer = OrderSigner(private_key)
        print(f"Signer Address: {signer.address}")
    except Exception as e:
        print(f"Error creating signer: {e}")
        return

    config = Config.from_env()
    print(f"Config loaded. Host: {config.clob.host}, ChainID: {config.clob.chain_id}, SigType: {config.clob.signature_type}")

    client = ClobClient(
        host=config.clob.host,
        chain_id=config.clob.chain_id,
        signature_type=config.clob.signature_type,
        funder=config.safe_address
    )

    print("\nAttempting to Create or Derive API Key...")
    try:
        creds = client.create_or_derive_api_key(signer)
        print("SUCCESS! Credentials obtained.")
        print(f"API Key: {creds.api_key}")
        print(f"Passphrase: {creds.passphrase}")
        # Don't print secret
    except Exception as e:
        print(f"FAILED to obtain credentials.")
        print(f"Error: {e}")
        if isinstance(e, ApiError):
            print("This is an API Error from Polymarket.")
        import traceback
        traceback.print_exc()
        return

    client.set_api_creds(creds)
    
    print("\nAttempting to fetch open orders (Authenticated Request)...")
    try:
        orders = client.get_open_orders()
        print(f"SUCCESS! Open orders fetched. Count: {len(orders)}")
    except Exception as e:
        print(f"FAILED to fetch open orders.")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auth()
