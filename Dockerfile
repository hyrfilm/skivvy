FROM python:2.7
RUN pip install skivvy
WORKDIR /app
CMD ["skivvy"]