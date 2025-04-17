FROM python:3

RUN mkdir /app
COPY ../config/log_config.yml /app/config/log_config.yml
COPY ../config/anomaly_detector/anomaly_config.yml /app/config/anomaly_detector/anomaly_config.yml
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt
RUN pip install --upgrade pip setuptools wheel
COPY . /app


RUN chown -R nobody:nogroup /app
USER nobody

EXPOSE 8080

ENTRYPOINT [ "python3" ]

CMD [ "app.py" ]
