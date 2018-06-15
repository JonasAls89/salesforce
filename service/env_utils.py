"""environment utility funcitons"""
import os

from flask import request


def get_var(var):
    if var.upper() in os.environ:
        return os.environ[var.upper()]
    env_var = request.args.get(var)
    return env_var
