FROM python:3

RUN mkdir /app

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt
RUN pip install --upgrade pip setuptools wheel
COPY . /app


RUN chown -R nobody:nogroup /app
USER nobody

EXPOSE 8090

ENTRYPOINT [ "sh", "-c" ]

CMD [ "python3 db_setup.py && python3 app.py" ]
