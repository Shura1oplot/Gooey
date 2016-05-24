# -*- coding: utf-8 -*-


class Taskbar(object):

    def __init__(self, hwnd):
        super(Taskbar, self).__init__()
        self.hwnd = hwnd

    def ensureState(self, state):
        pass

    def setState(self, state):
        pass

    def setValue(self, value, total=100):
        pass
