from .base import *
from decouple import config

DEBUG = config("DEBUG", cast=bool, default=True)
