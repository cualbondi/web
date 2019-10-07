from urllib import request
import os
import sys
from prefect import task


@task
def download_pbf(king):
    filename = f'/tmp/osm-{king["name"]}.pbf'
    url = king['url']
    request.urlretrieve(url, filename, lambda nb, bs, fs: progress(nb, bs, fs, url))


def progress(numblocks, blocksize, filesize, url):
    base = os.path.basename(url)
    try:
        percent = min((numblocks * blocksize * 100) / filesize, 100)
    except ZeroDivisionError:
        percent = 100
    if numblocks != 0:
        sys.stdout.write('\b' * 70)
    sys.stdout.write('%-66s%3d%%' % (base, percent))
