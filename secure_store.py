import json
import hashlib
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import keyring


def secure_hash(data):
    if not isinstance(data, str):
        try:
            data = json.dumps(data)
        except TypeError:
            raise ValueError("Data must be a string or JSON serializable object.")
    return hashlib.sha256(data.encode()).hexdigest()

def derive_key(password: str):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"",
        iterations=100000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt(data, password):
    if not isinstance(data, str):
        try:
            data = json.dumps(data)
        except TypeError:
            raise ValueError("Data must be a string or JSON serializable object.")
    key = derive_key(password)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    return iv + encryptor.update(base64.b64encode(data.encode())) + encryptor.finalize(), key

def decrypt(encrypted_data, key):
    iv = encrypted_data[:16]
    cipher = Cipher(algorithms.AES(derive_key(key)), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(encrypted_data[16:]) + decryptor.finalize()
    return base64.b64decode(decrypted_data).decode()

def passwordless_encrypt(data, name):
    if not isinstance(data, str):
        try:
            data = json.dumps(data)
        except TypeError:
            raise ValueError("Data must be a string or JSON serializable object.")
    key = os.urandom(algorithms.AES.block_size // 8)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    keyring.set_password(name, "", base64.b64encode(key).decode())
    return iv + encryptor.update(base64.b64encode(data.encode())) + encryptor.finalize(), key

def passwordless_decrypt(encrypted_data, name):
    key = keyring.get_password(name, "")
    if key is None:
        raise ValueError("No key found for passwordless decryption, please provide a password")
    key = base64.b64decode(key.encode())
    iv = encrypted_data[:16]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(encrypted_data[16:]) + decryptor.finalize()
    return base64.b64decode(decrypted_data).decode()

def secure_store(data, file_loc, password=None):
    if not isinstance(data, str):
        try:
            data = json.dumps(data)
        except TypeError:
            raise ValueError("Data must be a string or JSON serializable object.")
    if password is None:
        print("No password provided, initiating auto-password encryption.")
        print("WARNING: The file will NOT be decrypt-able on another machine.")
        print("WARNING: The file MUST keep the same name and location or it will not be decrypt-able.")
        encrypted_data, key = passwordless_encrypt(data, file_loc)
        with open(file_loc, "wb") as f:
            f.write(encrypted_data)
        keyring.set_password(file_loc, "", base64.b64encode(key).decode())
        return encrypted_data, key
    else:
        print("Password provided, initiating password encryption.")
        encrypted_data, key = encrypt(data, password)
        with open(file_loc, "wb") as f:
            f.write(encrypted_data)
        return encrypted_data, password

def secure_unstore(file_loc, password=None):
    if not os.path.isfile(file_loc):
        raise FileNotFoundError(f"File {file_loc} not found.")
    with open(file_loc, "rb") as f:
        encrypted_data = f.read()
    if password is None:
        key = keyring.get_password(file_loc, "")
        if key is None:
            raise ValueError("No key found for auto-password encryption, please provide a password")
        decrypted_data = passwordless_decrypt(encrypted_data, file_loc)
        return decrypted_data
    else:
        decrypted_data = decrypt(encrypted_data, password)
        return decrypted_data