"""Google TTS API key: hatena/tts_key.b64 is RSA-encrypted with piero/pub.pem; the private key piero/key.enc is Fernet-encrypted with YT_CLIENT_SECRET."""
import os, base64, hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
def tts_key():
    f = Fernet(base64.urlsafe_b64encode(hashlib.sha256(os.environ['YT_CLIENT_SECRET'].encode()).digest()))
    k = serialization.load_pem_private_key(f.decrypt(open(os.path.join(ROOT, 'piero/key.enc'), 'rb').read()), None)
    ct = base64.b64decode(open(os.path.join(HERE, 'tts_key.b64')).read().strip())
    return k.decrypt(ct, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)).decode().strip()
