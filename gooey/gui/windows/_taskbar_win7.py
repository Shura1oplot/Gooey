# -*- coding: utf-8 -*-

import comtypes.client as cc
import comtypes.gen.ShellObjects as sho


_taskbar = cc.CreateObject("{56FDF344-FD6D-11d0-958A-006097C9A090}",
                           interface=sho.ITaskbarList3)


TBPF_NOPROGRESS = 0x0
TBPF_INDETERMINATE = 0x1
TBPF_NORMAL = 0x2
TBPF_ERROR = 0x4
TBPF_PAUSED = 0x8


class Taskbar(object):

    _states = {
        "no_progress": TBPF_NOPROGRESS,
        "indeterminate": TBPF_INDETERMINATE,
        "normal": TBPF_NORMAL,
        "error": TBPF_ERROR,
        "paused": TBPF_PAUSED,
    }

    def __init__(self, hwnd):
        super(Taskbar, self).__init__()

        self.hwnd = hwnd
        self._last_state = None

    def ensureState(self, state):
        if self._last_state != state:
            self.setState(state)

    def setState(self, state):
        _taskbar.HrInit()
        _taskbar.SetProgressState(self.hwnd, self._states[state])
        self._last_state = state

    def setValue(self, value, total=100):
        _taskbar.HrInit()
        _taskbar.SetProgressValue(self.hwnd, int(value), int(total))
