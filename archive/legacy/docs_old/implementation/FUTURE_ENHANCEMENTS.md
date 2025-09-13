# Future Enhancements

## Config-Driven Settings UI (Priority: Medium)

**Issue**: Registry defines settings schemas but UI doesn't use them
- Registry has `settings_schema` for resistance_analysis: `{"time_points": {"type": "multiselect", "options": ["immediate", "10s", "30s"]}}`
- UI hardcodes basic widgets instead of rendering from schema
- Located in: `src_clean/panel_app/components/data_analysis_tab/analysis_panels.py:236-241`

**Solution**: Generic schema → widget renderer
```python
def _create_widget_from_schema(self, field_name: str, field_schema: Dict) -> pn.Widget:
    field_type = field_schema.get("type")
    if field_type == "multiselect":
        return pn.widgets.CheckBoxGroup(name=field_name, options=field_schema["options"])
    elif field_type == "float":
        return pn.widgets.FloatSlider(name=field_name, start=field_schema.get("min", 0))
    # ... etc
```

**Benefits**: 30-minute development workflow, consistent with registry-driven plotting system

**Effort**: Moderate - need schema parser + widget mapping

---

*Added: 2025-08-25 during registry system test drive*