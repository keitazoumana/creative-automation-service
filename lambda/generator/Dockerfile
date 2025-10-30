FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir --timeout=1000 --retries=10 -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org

COPY app.py ${LAMBDA_TASK_ROOT}/

CMD ["app.handler"]
