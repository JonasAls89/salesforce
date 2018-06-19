FROM python:3
MAINTAINER Timur Samkharadze "timur.samkharadze@sysco.no"
COPY ./service /opt/service
WORKDIR /opt
RUN pip install -r ./service/requirements.txt
EXPOSE 5000/tcp
ENTRYPOINT ["python"]
CMD ["./service/datasource_service.py"]
