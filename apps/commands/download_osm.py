import luigi
from urllib import request
import os
import sys


class ForceableTask(luigi.Task):

    force = luigi.BoolParameter(significant=False, default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # To force execution, we just remove all outputs before `complete()` is called
        if self.force is True:
            outputs = luigi.task.flatten(self.output())
            for out in outputs:
                if out.exists():
                    os.remove(self.output().path)


def progress(numblocks, blocksize, filesize, url):
    base = os.path.basename(url)
    try:
        percent = min((numblocks * blocksize * 100) / filesize, 100)
    except ZeroDivisionError:
        percent = 100
    if numblocks != 0:
        sys.stdout.write('\b' * 70)
    sys.stdout.write('%-66s%3d%%' % (base, percent))


class DownloadOSM(ForceableTask):
    king = None

    @classmethod
    def get_filename(cls):
        return f'/tmp/osm-{cls.king["name"]}.pbf'

    def output(self):
        return luigi.LocalTarget(self.get_filename())

    def run(self):
        url = self.king['url']
        request.urlretrieve(url, self.get_filename(), lambda nb, bs, fs: progress(nb, bs, fs, url))


class DownloadOSMArgentina(DownloadOSM):
    king = {
        'name': 'argentina',
        'url': 'http://download.geofabrik.de/south-america/argentina-latest.osm.pbf',
        'id': 286393,
        'paradas_completas': False,
    }
