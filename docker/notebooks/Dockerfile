FROM python:3.7

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev \
    gdal-bin \
  && rm -rf /var/lib/apt/lists/* \
  && pip install uwsgi

RUN groupadd django \
    && useradd django -s /bin/bash -m -g django -G django

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip install --no-cache-dir -r /requirements/production.txt \
    && pip install --no-cache-dir -r /requirements/notebooks.txt \
    && rm -rf /requirements

COPY ./docker/production/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN chown django /entrypoint.sh

COPY ./docker/notebooks/notebooks.sh /notebooks.sh
RUN sed -i 's/\r//' /notebooks.sh
RUN chmod +x /notebooks.sh
RUN chown django /notebooks.sh

COPY . /app

RUN chown -R django /app

USER django

RUN mkdir -p /home/django/.jupyter
COPY ./docker/notebooks/jupyter_notebook_config.py /home/django/.jupyter/

RUN mkdir -p /home/django/.local/share/jupyter/kernels/django_extensions
COPY ./docker/notebooks/kernel.json /home/django/.local/share/jupyter/kernels/django_extensions/

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8000
