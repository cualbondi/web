import threading


class PararellThread(threading.Thread):
    def __init__(self, qs, i):
        threading.Thread.__init__(self)
        self.qs = qs
        self.i = i
        self.result = []

    def run(self):
        self.result = list(self.qs)


def get_objects_in_pararell(querysets):
    threads = []
    results = [None] * len(querysets)
    for i in range(0, len(querysets)):
        qs = querysets[i]
        t = PararellThread(qs, i)
        t.start()
        threads.append(t)

    for thread in threads:
        thread.join()
        results[thread.i] = thread.result

    return results
