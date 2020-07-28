__version__ = '0.0.1'


def get_metrics(*args, **kwargs):
    from . import processing

    return processing.get_metrics(*args, **kwargs)
