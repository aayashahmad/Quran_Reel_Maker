# Website for Hugging Face Spaces (Docker). Serves on port 7860.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libraqm0 libfribidi0 \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as user 1000; give it a home and a writable app folder.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1 FFMPEG_THREADS=1
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY --chown=user . .
# Bake the Quran text and fonts into the image so the site starts instantly.
RUN python -c "from quran_data import load_quran; load_quran(); import video; video.ensure_fonts()"

EXPOSE 7860
# One worker: jobs are tracked in memory and renders run in background threads.
CMD ["gunicorn", "web:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "8", "--timeout", "0"]
