FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install with increased timeout
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir --timeout=1000 --retries=10 -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org

# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}/

# Set handler
CMD ["app.handler"]
