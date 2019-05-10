import threading
from django.db import connections


class PararellThread(threading.Thread):
    def __init__(self, qs, i, main_thread_connection):
        threading.Thread.__init__(self)
        self.qs = qs
        self.i = i
        self.result = []

    def run(self):
        from django.db import connections
        connections['default'].inc_thread_sharing()
        self.result = list(self.qs)
        connections['default'].close()
        connections['default'].dec_thread_sharing()


# Ideas from https://github.com/django/django/blob/ed880d92b50c641c3e7f6e8ce5741085ffe1f8fb/tests/backends/tests.py#L705
def parallelize(*querysets):
    threads = []
    results = [None] * len(querysets)
    for i in range(0, len(querysets)):
        qs = querysets[i]
        t = PararellThread(qs, i, connections['default'])
        t.start()
        threads.append(t)

    for thread in threads:
        thread.join()
        results[thread.i] = thread.result

    return results
