FROM python:3

RUN mkdir /app

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

COPY . /app

RUN chown -R nobody:nogroup /app
USER nobody

EXPOSE 8110

ENTRYPOINT [ "python3" ]

CMD [ "app.py" ]
