# AO Simulation demo — open-source voice (Kokoro TTS + faster-whisper STT).
# Decision 2026-10-20: Transcribe is SCP-denied in this project and Polly is
# proprietary; Kokoro-82M (Apache-2.0) + faster-whisper (MIT) run on CPU in
# this container instead. Models are baked in at build time so cold starts
# never download anything. Requires Docker at `cdk deploy` (AO_SIM_VOICE=1).
FROM public.ecr.aws/lambda/python:3.12

RUN pip install --no-cache-dir kokoro-onnx==0.4.9 soundfile==0.12.1 faster-whisper==1.1.1

# Kokoro model + voices (release assets from the kokoro-onnx project).
RUN curl -L -o /opt/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx \
 && curl -L -o /opt/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

# Pre-download the faster-whisper tiny model into the image.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8', download_root='/opt/whisper')"

COPY handler.py ${LAMBDA_TASK_ROOT}/
CMD ["handler.handler"]
