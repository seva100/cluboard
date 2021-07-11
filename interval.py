from time import sleep, time
from threading import Thread


class Interval(object):

    def __init__(self, interval, function, args=[], kwargs={}):
        """
        Runs the function at a specified interval with given arguments.
        """
        self.thread = Thread(target=self.run, args=())
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def start(self):
        self.thread.start()

    def run(self):
        while True:
            start_time = time()
            self.function(*self.args, **self.kwargs)
            # end_time = time()
            # sleep(max((start_time + self.interval) - end_time, 0))
            sleep(self.interval)
