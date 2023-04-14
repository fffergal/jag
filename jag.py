from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache


jags = ContextVar('jags', default={})

@contextmanager
def define(**kwargs):
    token = jags.set({**jags.get(), **kwargs})
    try:
        yield
    finally:
        jags.reset(token)


def getter(name):
    def get():
        return jags.get()[name]

    getter_name = f"get_{name}"
    get.__name__ = getter_name
    get.__qualname__ = getter_name
    return get


@cache
def __getattr__(name):
    if name.startswith("get_"):
        return getter(name[4:])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class Package:
    def __init__(self, pkg_name):
        self.pkg_name = pkg_name

    def define(self, **kwargs):
        return define(**{f"{k}.{self.pkg_name}": v for k, v in kwargs.items()})

    def getter(self, name):
        def get():
            return jags.get()[f"{name}.{self.pkg_name}"]

        get.__name__ = f"get_{name}"
        get.__qualname__ = f"{self.pkg_name}.get_{name}"
        return get

    @cache
    def __getattr__(self, name):
        if name.startswith("get_"):
            return self.getter(name[4:])
        raise AttributeError(
            f"module {'.'.join([__name__, self.pkg_name])!r} has no attribute {name!r}"
        )


class PkgMetaclass(type):
    @cache
    def __getattr__(cls, name):
        return Package(name)


class pkg(metaclass=PkgMetaclass):
    pass
