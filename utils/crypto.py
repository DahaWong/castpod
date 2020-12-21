from cryptography.fernet import Fernet
from config import encrypt_key

fernet = Fernet(encrypt_key)

def generate(passwd:str):
  passwd = str.encode(passwd)
  token = fernet.encrypt(passwd)
  return token 

def decrypt(token):
  passwd = fernet.decrypt(token)
  return passwd