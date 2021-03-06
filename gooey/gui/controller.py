'''
Created on Dec 22, 2013

@author: Chris
'''

import wx
import os
import re
import sys
import subprocess

from gooey.gui.pubsub import pub

from multiprocessing.dummy import Pool
from gooey.gui import events
from gooey.gui.lang import i18n
from gooey.gui.windows import views
from gooey.gui.util.taskkill import taskkill


YES = 5103
NO = 5104


class Controller(object):
  '''
  Main controller for the gui.

  All controlls are delegated to this central control point.
  '''

  def __init__(self, base_frame, build_spec):
    '''
    :type base_frame: BaseWindow
    :type build_spec: dict
    '''
    self.core_gui = base_frame
    self.build_spec = build_spec
    self._process = None
    self._stop_pressed_times = 0

    # wire up all the observers
    pub.subscribe(self.on_cancel,   events.WINDOW_CANCEL)
    pub.subscribe(self.on_stop,     events.WINDOW_STOP)
    pub.subscribe(self.on_start,    events.WINDOW_START)
    pub.subscribe(self.on_restart,  events.WINDOW_RESTART)
    pub.subscribe(self.on_close,    events.WINDOW_CLOSE)
    pub.subscribe(self.on_edit,     events.WINDOW_EDIT)

  def on_edit(self):
    pub.send_message(events.WINDOW_CHANGE, view_name=views.CONFIG_SCREEN)

  def on_close(self):
    if self.build_spec['disable_stop_button']:
      return
    if self.running():
      if not self.ask_stop():
        return
      self.stop(3)
    self.core_gui.Destroy()
    sys.exit()

  def on_restart(self):
    self.on_start()

  def manual_restart(self):
    self.on_start()

  def on_cancel(self):
    msg = i18n._('sure_you_want_to_exit')
    dlg = wx.MessageDialog(None, msg, i18n._('close_program'), wx.YES_NO)
    result = dlg.ShowModal()
    if result == YES:
      dlg.Destroy()
      self.core_gui.Destroy()
      sys.exit()
    dlg.Destroy()

  def on_start(self):
    if not self.skipping_config() and not self.required_section_complete():
      return self.show_dialog(i18n._('error_title'), i18n._('error_required_fields'), wx.ICON_ERROR)
    self._stop_pressed_times = 0
    cmd_line_args = self.core_gui.GetOptions()
    command = '{} --ignore-gooey {}'.format(self.build_spec['target'], cmd_line_args)
    pub.send_message(events.WINDOW_CHANGE, view_name=views.RUNNING_SCREEN)
    self.run_client_code(command)

  def on_stop(self):
    if self.build_spec['disable_stop_button']:
      return
    if not self.running():
      return
    if self._stop_pressed_times > 0 or self.ask_stop():
      self._stop_pressed_times += 1
      self.stop()

  def ask_stop(self):
    msg = i18n._('sure_you_want_to_stop')
    dlg = wx.MessageDialog(None, msg, i18n._('stop_task'), wx.YES_NO)
    result = dlg.ShowModal()
    dlg.Destroy()
    return result == YES

  def stop(self, urgency=None):
    if not self.running():
      return
    if urgency is None:
      urgency = self._stop_pressed_times
    taskkill(self._process.pid, urgency)

  def running(self):
    return self._process and self._process.poll() is None

  def run_client_code(self, command):
    print "run command:", command
    env = os.environ.copy()
    env["GOOEY"] = str(os.getpid())
    p = subprocess.Popen(command, bufsize=1, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, shell=True, env=env)
    self._process = p
    pool = Pool(1)
    pool.apply_async(self.read_stdout, (p, self.process_result))

  def read_stdout(self, process, callback):
    while True:
      line = process.stdout.readline()
      if not line:
        break
      progress = self.progress_from_line(line)
      if progress is not None:
        wx.CallAfter(self.core_gui.UpdateProgressBar, progress)
      if progress is None or not self.build_spec['progress_consume_line']:
        wx.CallAfter(self.core_gui.PublishConsoleMsg, line)
    wx.CallAfter(callback, process)

  def progress_from_line(self, text):
    progress_regex = self.build_spec['progress_regex']
    if not progress_regex:
      return None
    match = re.search(progress_regex, text.strip())
    if not match:
      return None
    progress_expr = self.build_spec['progress_expr']
    if progress_expr:
      return self._eval_progress(match, progress_expr)
    else:
      return self._search_progress(match)

  def _search_progress(self, match):
    try:
      return int(float(match.group(1)))
    except:
      return None

  def _eval_progress(self, match, eval_expr):
    def safe_float(x):
      try:
        return float(x)
      except ValueError:
        return x
    _locals = {k: safe_float(v) for k, v in match.groupdict().items()}
    if "x" not in _locals:
      _locals["x"] = [safe_float(x) for x in match.groups()]
    try:
      return int(float(eval(eval_expr, {}, _locals)))
    except:
      return None

  def process_result(self, process):
    process.communicate()
    if self._stop_pressed_times > 0:
      wx.CallAfter(self.core_gui.PublishConsoleMsg, i18n._('terminated'))
      pub.send_message(events.WINDOW_CHANGE, view_name=views.ERROR_SCREEN)
      self.terminated_dialog()
    elif process.returncode == 0:
      pub.send_message(events.WINDOW_CHANGE, view_name=views.SUCCESS_SCREEN)
      self.success_dialog()
    else:
      pub.send_message(events.WINDOW_CHANGE, view_name=views.ERROR_SCREEN)
      self.error_dialog()

  def skipping_config(self):
    return self.build_spec['manual_start']

  def required_section_complete(self):
    required_section = self.core_gui.GetRequiredArgs()
    if len(required_section) == 0:
      return True  # no requirements!
    return not any(req == '' for req in required_section)

  def success_dialog(self):
    self.show_dialog(i18n._("execution_finished"), i18n._('success_message'), wx.ICON_INFORMATION)

  def error_dialog(self):
    self.show_dialog(i18n._('error_title'), i18n._('uh_oh'), wx.ICON_ERROR)

  def terminated_dialog(self):
    self.show_dialog(i18n._('error_title'), i18n._('terminated'), wx.ICON_ERROR)

  def show_dialog(self, title, content, style):
    a = wx.MessageDialog(None, content, title, style)
    a.ShowModal()
    a.Destroy()
