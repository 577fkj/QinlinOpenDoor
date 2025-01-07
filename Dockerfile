FROM python:3.13

WORKDIR /app
ADD requirements.txt /app
ADD server.py /app
ADD qinlinAPI.py /app
ADD templates /app/templates
ADD static /app/static

RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

CMD ["python3", "server.py"]