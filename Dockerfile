FROM python:3.9-slim

# Create a non-root user and group
RUN groupadd -r nonroot -g 999 && useradd -m -r -g nonroot -u 999 nonroot

RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    iproute2 \
    procps \
    lsof \
    net-tools \
    tcpdump \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code
RUN chown nonroot:nonroot /code

# Copy requirements first for better cache utilization
COPY --chown=nonroot:nonroot requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=nonroot:nonroot app app/

# Set proper permissions for all copied files
# This ensures files are readable and executable where needed
RUN chmod -R u=rwX,g=rX,o= /code && \
    # Ensure the nonroot user owns all files
    chown -R nonroot:nonroot /code

# Expose the port the app runs on
EXPOSE 8000

# Switch to the non-root user
USER nonroot

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]