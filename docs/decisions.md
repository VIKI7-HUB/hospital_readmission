# Modeling and design decisions

1. Patient-level split: Encounters were grouped by `patient_nbr` so all encounters for any individual patient reside in exactly one split (70% train, 10% validation, 20% test).
   Alternative rejected: Encounter-level random splitting, which leaks patient identity and chronic disease patterns across folds.

2. Caps fit on the training split: Capping values for continuous variables were fit on the training partition only (at the 99th percentile) and applied to validation and test sets.
   Alternative rejected: Dataset-wide capping, which leaks distribution tails from future data into model training.

3. Recall-first threshold rule: The decision threshold was chosen to meet or exceed a clinical recall target (>= 60%) on the validation set.
   Alternative rejected: A default 0.50 cutoff or an accuracy-maximizing threshold, which flags almost no patients in an imbalanced 11% readmission scenario.

4. Probability calibration on validation data: Platt scaling (sigmoid calibration) was fit on independent validation predictions and selected via cross-validated Brier score.
   Alternative rejected: Using uncalibrated raw scores or fitting calibration on training or test splits.

5. Single champion model: A single transparent random forest model was selected based on the simpler-model hierarchy within 0.005 of peak PR-AUC.
   Alternative rejected: Complex multi-model voting ensembles or stacking, which add runtime dependencies and obscure individual tree contributions.

6. Balanced class weighting instead of resampling: Synthetic resampling (SMOTE) or random undersampling was omitted in favor of cost-sensitive class weights during training.
   Alternative rejected: Resampling, which distorts baseline calibrated probabilities and discards useful clinical encounters.

7. Native TreeSHAP explainability: Feature contributions were computed using exact tree structure traversal (TreeSHAP) without approximation.
   Alternative rejected: Kernel SHAP or permutation importance, which are slow, stochastic, and less consistent.

8. Streamlit interface: Streamlit was used for the entire clinical application.
   Alternative rejected: Multi-tier web stacks (such as React with FastAPI), which add networking overhead, multi-process operational complexity, and maintenance burden.

9. Classical machine learning without language models: Predictions and explanations are derived strictly from scikit-learn models, TreeSHAP values, and fixed clinical templates.
   Alternative rejected: Generative AI or large language models, which can hallucinate patient facts, require external network calls, and lack verifiable deterministic outputs.

10. Subgroup thresholds for analysis only: Group-specific classification thresholds were computed as an exploratory fairness reference.
    Alternative rejected: Deploying group-varying decision cutoffs in clinical production, which requires collecting and utilizing protected demographic attributes at the point of care.
