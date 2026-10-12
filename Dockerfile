# The website as a container: used for the free backup server on Render (render.yaml).
# Serves on $PORT (Render sets it; 7860 otherwise).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libraqm0 libfribidi0 curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1 FFMPEG_THREADS=1
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY --chown=user . .
# Bake everything the site reads into the image so it starts at once: the Quran text and fonts, the English
# translation, the moving backgrounds (deploy/bg), Sahih al-Bukhari / Muslim (fawazahmed0/hadith-api, public
# domain) and the Ask the Quran search index.
RUN mkdir -p data/bg data/hadith && cp deploy/bg/*.mp4 data/bg/ \
    && for f in eng-bukhari urd-bukhari eng-muslim urd-muslim; do \
         curl -sfL --retry 3 -o data/hadith/$f.json "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/$f.json"; \
       done \
    && python -c "from quran_data import load_quran; q = load_quran(); import video; video.ensure_fonts(); \
from translations import texts; texts('en', q); import quran_search; quran_search._db().close()"

EXPOSE 7860
# One worker: jobs are tracked in memory.
CMD ["sh", "-c", "exec gunicorn web:app --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 8 --timeout 120"]
