.PHONY: install test agent crm demo

install:
	python -m pip install -e '.[test]'

test:
	python -m pytest -ra

agent:
	uvicorn app.main:app --reload --env-file .env

crm:
	uvicorn app.crm:crm_app --reload --port 8001 --env-file .env

demo:
	python tools/demo_call.py --voice "$${PIPER_VOICE_PATH:?Set PIPER_VOICE_PATH to a local Piper ONNX voice}" --model "$${OLLAMA_MODEL:-qwen3:1.7b}" --output docs/demo-output.txt
