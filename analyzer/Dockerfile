FROM python:3

RUN mkdir -p /app/data

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

COPY . /app

# Ensure nobody owns everything
RUN chown -R nobody:nogroup /app

USER nobody

EXPOSE 8100

ENTRYPOINT [ "python3" ]
CMD [ "app.py" ]
