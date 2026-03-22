## Reporting API (exact signatures)

Document your project's reporting API here with EXACT call syntax.
Agents will hallucinate keyword args unless every argument is shown explicitly.

Example (replace with your actual API):
```python
# sr = stat_result("test name", statistic=0.0, p_value=0.001, effect_size=2.5)
# f = finding("description", [sr], confidence_level=0.9)
# json_str = findings_to_json([f1, f2])  # returns STRING
# with open('findings.json', 'w') as fh:
#     fh.write(json_str)
```
