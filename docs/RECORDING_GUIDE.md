# Recording guide

Real-recording collection is **NOT EXECUTED** until the author records and annotates the requested minimum of 40 consented utterances. Do not record customer data. Use a quiet environment and save mono PCM WAV with the sample rate stated in the manifest. Store names as random speaker IDs, not names. Keep English and optional Hinglish subsets separate. Review and correct each reference transcript before running WER.

Create one CSV manifest row per utterance with `path,reference,language,split,data_type`. Keep the dataset outside Git. Synthetic TTS/noise variants must be marked `SYNTHETIC` and reported separately from real recordings. A small synthetic sample was generated using Piper and deterministic Gaussian noise; see `RESULTS.md`.

Run `python tools/make_dataset.py --manifest <csv> --output <summary.json>` to validate inventory; it requires at least 40 rows marked `REAL`. The script never downloads or invents recordings.

For generated audio, run `python tools/make_synthetic_dataset.py --voice <voice.onnx> --output <outside-repo-dir>`. Generate hypotheses with `python tools/run_asr_dataset.py --manifest <manifest.csv> --output <hypotheses.csv> --model base.en --device cpu --compute-type int8`, then run `python tools/evaluate_wer.py --manifest <manifest.csv> --hypotheses <hypotheses.csv>`.
