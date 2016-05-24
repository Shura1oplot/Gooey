# -*- coding: utf-8 -*-

import platform


__all__ = ("Taskbar", )


def _taskbar_api_available():
    def _safe_int(x):
        try:
            return int(x)
        except ValueError:
            return x

    return platform.system() == "Windows" and \
        tuple(_safe_int(x) for x in platform.version().split(".")) >= (6, 1)


if _taskbar_api_available():
    from ._taskbar_win7 import Taskbar
else:
    from ._taskbar_dummy import Taskbar
