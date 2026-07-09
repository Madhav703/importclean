"""Utility module with a partially-used import."""
from os import path, mkdir, remove

def get_path(name):
    return path.join("/tmp", name)
