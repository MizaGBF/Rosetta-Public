FROM python:3.13
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN apt-get update && apt-get install --yes --no-install-recommends libjemalloc2
ENV PYTHONMALLOC=malloc \
    PYTHONUNBUFFERED=1 \
    LD_PRELOAD=libjemalloc.so.2
CMD ["python", "-O", "bot.py", "-r"]