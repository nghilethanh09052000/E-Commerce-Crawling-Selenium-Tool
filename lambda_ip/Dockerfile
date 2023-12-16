FROM public.ecr.aws/lambda/python:3.8

ARG ENVIRONMENT_NAME=production
ENV ENVIRONMENT_NAME="${ENVIRONMENT_NAME}"

#Perform a quick update on your instance:
RUN yum update -y \
    && yum install which -y \
    && yum install git -y \
    && yum install gcc -y \
    && yum install gcc-c++ -y

# Copy function code
COPY ./lambda_ip ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "get_ip.handler" ]
