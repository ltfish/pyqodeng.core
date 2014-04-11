# -*- coding: utf-8 -*-
"""
Contains utility functions
"""
import collections
import functools
import sys
import weakref

from PyQt4 import QtCore, QtGui

from pyqode.core import logger
from pyqode.core.frontend.decoration import TextDecoration


class memoized(object):
    """
    Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        try:
            if not isinstance(args, collections.Hashable):
                # uncacheable. a list, for instance.
                # better to not cache than blow up.
                return self.func(*args)
            if args in self.cache:
                return self.cache[args]
            else:
                value = self.func(*args)
                self.cache[args] = value
                return value
        except TypeError:
            return self.func(*args)

    def __repr__(self):
        """ Return the function's docstring."""
        return self.func.__doc__

    def __get__(self, obj, objtype):
        """ Support instance methods. """
        return functools.partial(self.__call__, obj)


def merged_colors(color_a, color_b, factor):
    max_factor = 100
    color_a = QtGui.QColor(color_a)
    color_b = QtGui.QColor(color_b)
    tmp = color_a
    tmp.setRed((tmp.red() * factor) / max_factor +
               (color_b.red() * (max_factor - factor)) / max_factor)
    tmp.setGreen((tmp.green() * factor) / max_factor +
                 (color_b.green() * (max_factor - factor)) / max_factor)
    tmp.setBlue((tmp.blue() * factor) / max_factor +
                (color_b.blue() * (max_factor - factor)) / max_factor)
    return tmp


def drift_color(base_color, factor=110):
    """
    Return a near color that is lighter or darker than the base color.

    If baseColor.lightness is higher than 128 than darker is used else lighter
    is used.

    :param base_color: The base color to drift.

    :return A lighter or darker color.
    """
    base_color = QtGui.QColor(base_color)
    if base_color.lightness() > 128:
        return base_color.darker(factor)
    else:
        if base_color == QtGui.QColor('#000000'):
            return QtGui.QColor('#202020')
        else:
            return base_color.lighter(factor + 10)


def index_matching(seq, condition):
    """
    Returns the index of the element that match condition.

    :param seq: The sequence to parse

    :param condition: The index condition

    :return: Index of the element that mathc the condition of -1
    """
    for i, x in enumerate(seq):
        if condition(x):
            return i
    return -1


def index_by_name(seq, name):
    """
    Search an element by "name".

    :param seq: Sequence to parse

    :param name: Name of the element

    :return: Index of the element of -1
    """
    return index_matching(seq, lambda x: x.name == name)


class TextStyle(object):
    """
    Helper class to define a text format. This class has methods to set the
    text style from a string and to easily be created from a string, making
    serialisation extremely easy.

    A text style is made up of a text color and a series of text attributes:

        - bold/nbold
        - italic/nitalic
        - underlined/nunderlined.

    Example of usage::

        style = TextStyle('#808000 nbold nitalic nunderlined')
        print(style)  #should print '#808000 nbold nitalic nunderlined'

    """

    def __init__(self, style=None):
        """
        :param style: The style string ("#rrggbb [bold] [italic] [underlined])
        """
        self.color = QtGui.QColor()
        self.bold = False
        self.italic = False
        self.underlined = False
        if style:
            self.from_string(style)

    def __repr__(self):
        color = self.color.name()
        bold = "nbold"
        if self.bold:
            bold = "bold"
        italic = "nitalic"
        if self.italic:
            italic = "italic"
        underlined = "nunderlined"
        if self.underlined:
            underlined = "underlined"
        return " ".join([color, bold, italic, underlined])

    @memoized
    def from_string(self, string):
        tokens = string.split(" ")
        assert len(tokens) == 4
        self.color = QtGui.QColor(tokens[0])
        self.bold = False
        if tokens[1] == "bold":
            self.bold = True
        self.italic = False
        if tokens[2] == "italic":
            self.italic = True
        self.underlined = False
        if tokens[3] == "underlined":
            self.underlined = True


def inheritors(klass):
    """
    Returns all the class that inherits from klass (all the classes that
    were already imported)

    :param klass: class type

    :return: list of subclasses
    """
    subclasses = set()
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses


class _InvokeEvent(QtCore.QEvent):
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, fn, *args, **kwargs):
        QtCore.QEvent.__init__(self, _InvokeEvent.EVENT_TYPE)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class _Invoker(QtCore.QObject):
    def event(self, event):
        event.fn(*event.args, **event.kwargs)
        return True


class _JobThread(QtCore.QThread):
    """
    Runs a callable into a QThread. The thread may be stopped at anytime using
    the stopJobThreadInstance static method.
    """

    _name = "JobThread({}{}{})"

    def __init__(self):
        QtCore.QThread.__init__(self)
        self._job_results = None
        self.used = False
        self.args = ()
        self.kwargs = {}
        self.execute_on_run = None
        self.execute_on_finish = None

    @staticmethod
    def stop_job_thread(caller, method, *args, **kwargs):
        caller.invoker = _Invoker()
        caller.invoke_event = _InvokeEvent(method, *args, **kwargs)
        QtCore.QCoreApplication.postEvent(caller.invoker, caller.invoke_event)

    def __repr__(self):
        if hasattr(self, "executeOnRun"):
            name = self.execute_on_run.__name__
        else:
            name = hex(id(self))
        return self._name.format(name, self.args, self.kwargs)

    def stop_run(self):
        self.on_finish()
        self.terminate()
        self.used = False
        self.set_methods(None, None)

    def set_methods(self, on_run, on_finish):
        self.execute_on_run = on_run
        self.execute_on_finish = on_finish

    def set_parameters(self, *a, **kw):
        self.args = a
        self.kwargs = kw

    def on_finish(self):
        if (hasattr(self, "execute_on_finish") and self.execute_on_finish
                and hasattr(self.execute_on_finish, '__call__')):
            self.execute_on_finish()

    def run(self):
        try:
            self.execute_on_run(*self.args, **self.kwargs)
        except AttributeError:
            logger.warning("Executing not callable statement: %s" %
                           self.execute_on_run)
        else:
            self.on_finish()
            self.used = False
            self.set_methods(None, None)


class JobRunner(object):
    """
    Utility class to easily run an asynchroneous job. A job is a simple
    callable (method) that will be run in a background thread.

    JobRunner implements a job queue to ensure there is only one job running
    per JobRunner instance. If a job is already running, the new job will wait
    for the current job to finish unless you want to force its execution. It
    that case the current job will be terminated.

    Additional parameters can be supplied to the job using args and kwargs.

    .. code-block:: python

        self.jobRunner = JobRunner(self)
        self.jobRunner.startJob(self.aJobMethod)

    .. warning:: Do not manipulate QWidgets from your job method. Use
                 signal/slots to propagate changes to the ui.
    """
    @property
    def caller(self):
        return self._caller()

    @property
    def job_running(self):
        return self._job_running

    def __init__(self, caller, nb_threads_max=3):
        """
        :param caller: The object that will ask for a job to be run. This must
        be a subclass of QObject.
        """
        self._caller = weakref.ref(caller)
        self._job_queue = []
        self._threads = []
        self._job_running = False
        for i in range(nb_threads_max):
            self._threads.append(_JobThread())

    def __repr__(self):
        return repr(self._job_queue[0] if len(self._job_queue) > 0 else "None")

    def find_unused_threads(self):
        for thread in self._threads:
            if not thread.used:
                return thread
        return None

    def start_job(self, job, force, *args, **kwargs):
        """
        Starts a job in a background thread.

        :param job: job.
        :type job: callable

        :param force: Specify if we must force the job execution by stopping
                      the job that is currently running (if any).
        :type force: bool

        :param args: args
        :param kwargs: kwargs
        """
        thread = self.find_unused_threads()
        if thread:
            thread.set_methods(job, self._execute_next)
            thread.set_parameters(*args, **kwargs)
            thread.used = True
            if force:
                self._job_queue.append(thread)
                self.stop_job()
            else:
                self._job_queue.append(thread)
            if not self._job_running:
                self._job_queue[0].set_methods(job, self._execute_next)
                self._job_queue[0].set_parameters(*args, **kwargs)
                self._job_running = True
                self._job_queue[0].start()
            return True
        else:
            logger.debug("Failed to queue job. All threads are used")
            return False

    def _execute_next(self):
        self._job_running = False
        if len(self._job_queue) > 0:
            self._job_queue.pop(0)
        if len(self._job_queue) > 0:
            self._job_queue[0].start()
            self._job_running = True
            self._job_queue[0].used = True

    def stop_job(self):
        """
        Stops the current job
        """
        if len(self._job_queue) > 0:
            _JobThread.stop_job_thread(
                self.caller, self._job_queue[0].stop_run)


class DelayJobRunner(JobRunner):
    """
    Extends the JobRunner to introduce a delay between the job request and the
    job execution. If a new job is requested, the timer is stopped discarding a
    possible waiting job.

    This is heavily used internally for situations where the user can cancel a
    job (code completion, calltips,...).
    """
    def __init__(self, caller, nb_threads_max=3, delay=500):
        JobRunner.__init__(self, caller, nb_threads_max=nb_threads_max)
        self._timer = QtCore.QTimer()
        self._interval = delay
        self._timer.timeout.connect(self._exec_requested_job)
        self._args = []
        self._kwargs = {}

    def request_job(self, job, async, *args, **kwargs):
        """
        Request a job execution. The job will be executed after the delay
        specified in the DelayJobRunner contructor elapsed if no other job is
        requested until then.

        :param job: job.
        :type job: callable

        :param async: Specify if the job should be run asynchronously
        :type async: bool

        :param force: Specify if we must force the job execution by stopping
                      the job that is currently running (if any).
        :type force: bool

        :param args: args
        :param kwargs: kwargs
        """
        self._timer.stop()
        self._job = job
        self._args = args
        self._kwargs = kwargs
        self._async = async
        self._timer.start(self._interval)

    def cancel_requests(self):
        """
        Cancels pending requests.
        """
        self._timer.stop()

    def _exec_requested_job(self):
        """
        Execute the requested job after the timer has timeout.
        """
        self._timer.stop()
        if self._async:
            self.start_job(self._job, False, *self._args, **self._kwargs)
        else:
            self._job(*self._args, **self._kwargs)
        # self._job = None
        # self._args = None
        # self._kwargs = None
        # self._async = None


if __name__ == '__main__':
    import time
    from pyqode.core.frontend import QCodeEdit

    class Example(QCodeEdit):

        addDecorationRequested = QtCore.pyqtSignal(str, int)

        def __init__(self):
            QCodeEdit.__init__(self, parent=None)
            self.open_file(__file__)
            self.resize(QtCore.QSize(1000, 600))
            self.addDecorationRequested.connect(self.decorate_line)

        def showEvent(self, event):
            QCodeEdit.showEvent(self, event)
            self.job_runner = JobRunner(self, nb_threads_max=3)
            self.job_runner.start_job(self.xxx, False, "#FF0000", 0)
            self.job_runner.start_job(self.xxx, False, "#00FF00", 10)
            self.job_runner.start_job(self.xxx, False, "#0000FF", 20)

        def decorate_line(self, color, line):
            tc = self.textCursor()
            tc.setPosition(0)
            tc.movePosition(QtGui.QTextCursor.Down,
                            QtGui.QTextCursor.MoveAnchor,
                            line)
            d = TextDecoration(tc)
            d.set_as_error(QtGui.QColor(color))
            d.set_full_width(True)
            self.add_decoration(d)

        def xxx(self, color, offset):
            for i in range(10):
                line = i + offset
                print("Decorate line {0} with color {1} from a background "
                      "thread".format(line, color))
                self.addDecorationRequested.emit(color, line)
                time.sleep(0.1)
            if offset == 10:
                self.job_runner.start_job(self.xxx, False, "#FF00FF", 30)
            print("Finished")

    app = QtGui.QApplication(sys.argv)
    e = Example()
    e.show()
    sys.exit(app.exec_())