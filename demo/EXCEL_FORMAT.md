# Excel File Format for PT Curve Comparison

## File Structure

When uploading .xlsx files to the PT曲线对比 (PT Curve Comparison) tab, the system expects the following format:

### Row Structure
- **Rows 1-4**: Header/metadata rows (SKIPPED by the system)
- **Row 5 onwards**: Actual data

### Column Structure
- **Column 1 (First column)**: X-axis data (Time in ms)
- **Column 2 (Second column)**: Y-axis data (Pressure in MPa)

## Example File Structure

```
Row 1:  [Header Info 1]    [Header Info 1]
Row 2:  [Header Info 2]    [Header Info 2]
Row 3:  [Header Info 3]    [Header Info 3]
Row 4:  [Header Info 4]    [Header Info 4]
Row 5:  0                   0
Row 6:  1                   2.2
Row 7:  2                   4.4
Row 8:  3                   6.6
...     ...                 ...
```

## Notes
- The first 4 rows can contain any metadata, headers, or information - they will be skipped
- Column headers are not required (since first 4 rows are skipped)
- Only the first two columns are read; additional columns are ignored
- Data rows with empty/null values will be automatically dropped
- The system will use as many data rows as available after row 4

## Sample File
A sample file is provided at: `demo/data/测试数据_NC50.xlsx`

## File Naming Convention (Recommended)
`<test_name>_NC<value>.xlsx`

Example: `测试数据_NC50.xlsx` for NC用量1 = 50mg
