# Benchmark Analysis Task

You are an analysis agent. Perform a complete analysis on the provided dataset following the skill protocol EXACTLY.

## Dataset
- **Path**: {{dataset_path}}
- **Description**: {{dataset_description}}
- **Key columns**: {{column_descriptions}}

## Instructions
1. Read the skill protocol at `{{skill_path}}`
2. Write your analysis script at `{{output_dir}}/analysis_code.py`
3. Follow the code blocks in the skill EXACTLY — do not deviate from the prescribed function calls and parameters
4. {{dataset_specific_notes}}

## Setup
- Create the output directory with `os.makedirs` before writing files
- Add `sys.path.insert(0, 'src')` before importing from the analytics toolkit
- Set `matplotlib.use('Agg')` before importing pyplot

## Required Outputs
- `analysis_code.py` — the complete analysis script
- `findings.json` — serialized findings via `findings_to_json()`
- `summary.json` — key metrics summary (must include all relevant numeric metrics)
- All figures as PDF files via `save_fig()`

## Report Format
After execution, report:
1. Whether the script completed successfully
2. All numeric metrics from summary.json (C-statistic, ARI, DE gene count, etc.)
3. Key findings (significant covariates, clusters found, etc.)
4. Any errors encountered and how they were resolved
5. List of output files generated
