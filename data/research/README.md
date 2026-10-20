# Research data and composite context

The research pipeline imports actual de-identified CGM, heart-rate and interbeat-interval observations from [PhysioNet BIG IDEAs v1.1.3](https://physionet.org/content/big-ideas-glycemic-wearable/1.1.3/). It pairs these with separately sourced Synthea profiles for the interface and a negative-control experiment. **These are different people.** The composite is not a real longitudinal clinical record.

The primary prediction model is selected using participant-held-out development performance. Eligible models use CGM alone, CGM with HR/RMSSD, or those signals plus source-matched research HbA1c/sex. Synthetic EHR-only and synthetic EHR-plus-wearable models are evaluated separately. An arbitrary composite cannot establish a physiological benefit from EHR fusion.

## Sources and licenses

- **Wearables:** Cho, P., Kim, J., Bent, B., and Dunn, J. (2026), BIG IDEAs Lab Glycemic Variability and Wearable Device Data, version 1.1.3. [DOI](https://doi.org/10.13026/aw6y-fc44). Files use the **Open Data Commons Attribution License v1.0**; see [the retained license](PHYSIONET_LICENSE.txt). Also cite Bent et al., *Engineering digital biomarkers of interstitial glucose from noninvasive smartwatches* (2021), [DOI](https://doi.org/10.1038/s41746-021-00465-w).
- **Synthetic EHR:** the official Synthea sample archive at immutable repository commit `2c7d489eb4c8bc967dbfab3499a0f573818880dc`. Archive SHA-256 `a7f6f24d3ebd96bbf0b5ef29a16ca6bd6d7ca68db65537ca6ccab6adc20ec609`. Source terms and field-level details are in [synthea-provenance.json](synthea-provenance.json). The official download page permits unrestricted use. Cite Walonoski et al. (2018), [DOI](https://doi.org/10.1093/jamia/ocx079).
- **Application code:** MIT. The application license does not replace external data licenses.

The PhysioNet signal files may be retrieved from its official public version 1.1.2 S3 mirror because each selected file is verified against the **version 1.1.3 publisher SHA-256**, not merely assumed equivalent. Version 1.1.3 changed food logs, which are not model inputs. [Publisher checksums](PHYSIONET_SHA256SUMS.txt) are retained. Raw CSV files stay in ignored `work/`.

## What is measured and what is derived

- Glucose: actual Dexcom EGV observations, mg/dL. Metadata and identity-like export header rows are excluded.
- HR: mean of valid observations in the completed five-minute interval, bpm. Minute-rounded timestamps are delayed by one minute before aggregation, preventing within-minute lookahead.
- HRV: **IBI-derived RMSSD**, milliseconds, from accepted successive intervals in a completed five-minute bin. At least 20 pairs are required; gaps over ten seconds are not bridged. This is not clinical ECG-derived HRV.
- Sleep stages, step counts, accelerometry-derived activity and genetic markers: **unavailable**, not synthesized.
- Matched research HbA1c and sex: supplied in PhysioNet `Demographics.csv`. HbA1c has no measurement timestamp, so its use as pre-existing baseline information is an explicit assumption.
- Synthetic age, diagnoses, labs and medications: imported Synthea source rows available at the independent `2019-01-01` snapshot. Missing fields stay null. These do not describe the wearable participant.

Source dates were shifted by the dataset publisher. The timezone was not supplied. JSON timestamps use `Z` as a neutral sortable encoding of the source clock, not a verified UTC collection time.

## Prediction target and temporal boundaries

Continuous forecasts target approximately **+30, +60, +90 and +120 minutes**. Evaluation uses the nearest actual source CGM observation within **±150 seconds** of each nominal horizon. Future measurements are never interpolated.

The train-only prevalence audit found 122 of 6,704 windows at or above 180 mg/dL (1.82%). That failed the declared support rule. The selected classification target is therefore a **rise of at least 20 mg/dL by approximately +120 minutes**, relative to the latest available current glucose value. It had 1,074 of 6,704 positive training windows (16.02%), across all nine training participants. It is a research endpoint, not a medical diagnosis.

Features use only the six-hour prefix ending at the chosen prediction time. CGM may be carried forward for at most 15 minutes, with recency exposed. No backward fill, future interpolation, meals, future activity or latent simulator values enter the model. Raw future truth is exported separately in `research-truth.json` and consulted only after a prediction is frozen.

## Evaluation

The protocol fixes source participants 001–009 for fitting, 010–011 for model selection, 012–013 for calibration, and 014–016 for final evaluation. Adjacent windows from the same person never cross partitions. Model settings are chosen before final participants are processed. The model, all ablations, calibration bands, thresholds, source fingerprints and fitted cache are frozen before final scoring.

Only two calibration and three final participants are available. This is a small convenience-cohort experiment, not clinical validation. Metrics count overlapping windows, not independent adverse episodes. Empirical residual bands and Platt calibration may fail under new participants or corrupted signals. Numerical results from the older synthetic model are a separate legacy experiment and cannot be presented as this model's performance.

## Reproduce into an isolated output folder

```sh
python -m pip install -r ml/requirements.txt
python scripts/ingest_synthea.py
python scripts/ingest_wearable.py
python ml/train_research.py --phase develop --output-dir work/reproduced-research --work-dir work/reproduced-research-cache
python ml/train_research.py --phase evaluate --output-dir work/reproduced-research --work-dir work/reproduced-research-cache
```

The develop command refuses to overwrite an existing frozen research artifact. Final evaluation refuses to restart after its recorded start. The separate folder retains the new audit trail without changing the published artifacts. Do not remove audit locks to silently rerun the published experiment. The checked-in model's Python/JavaScript parity fixtures can be verified with `node --test tests/research-model.test.mjs`.
