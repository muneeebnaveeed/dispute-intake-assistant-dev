# Conda-native build: the same environment.yml works on a machine with Anaconda installed
# (`conda env create -f environment.yml`) and inside this image.
FROM anaconda/miniconda:latest

WORKDIR /app
# conda-forge only: the image's config lists Anaconda's default channels, which now require
# accepting Terms of Service. Removing them keeps the env fully open-source and non-interactive.
RUN conda config --system --remove channels defaults || true \
 && conda config --system --add channels conda-forge \
 && conda config --system --set channel_priority strict

COPY environment.yml .
RUN conda env create -f environment.yml && conda clean -afy

# Put the env's binaries first so `python`, `pytest`, `streamlit` resolve without `conda run`.
ENV PATH=/opt/miniconda3/envs/dispute-intake/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
