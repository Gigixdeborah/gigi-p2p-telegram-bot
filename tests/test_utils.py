import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils import validate_address


def test_validate_address():
    assert validate_address('UQCMbQomO3XD1FSt7pyfjqj2jBRzyg23myKDtCky_CedKpEH', 'TON')
    assert validate_address('0x4fb9055c71a3cafd7c6d30686cfe55282a11ac5e', 'EVM')
    assert validate_address('CdkLzLG3uTwA7HqNGZ3CC4fTc4EwjGJWaTGNjmTRpu7Z', 'Solana')
    assert not validate_address('badaddress', 'TON')
