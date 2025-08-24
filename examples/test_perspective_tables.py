import panel as pn
import pandas as pd

# Enable Panel extensions
pn.extension('perspective')

# Create fake hierarchical data mimicking your cell/file structure
fake_data = [
    # Cell-level rows
    {'name': 'CELL_01', 'type': 'cell', 'chemistry': 'Li-ion', 'capacity_ah': 2.5, 'files': 3, 'material': 'NMC811',
     'status': 'Active', 'parent': None},
    {'name': 'CELL_02', 'type': 'cell', 'chemistry': 'Li-metal', 'capacity_ah': 3.0, 'files': 2, 'material': 'LFP',
     'status': 'Active', 'parent': None},
    {'name': 'CELL_03', 'type': 'cell', 'chemistry': 'Li-ion', 'capacity_ah': 2.2, 'files': 4, 'material': 'NCA',
     'status': 'Active', 'parent': None},

    # File-level rows for CELL_01
    {'name': 'exp_001.par', 'type': 'file', 'chemistry': None, 'capacity_ah': None, 'files': None, 'material': None,
     'status': '✓ Processed', 'parent': 'CELL_01'},
    {'name': 'exp_002.par', 'type': 'file', 'chemistry': None, 'capacity_ah': None, 'files': None, 'material': None,
     'status': '⏳ Processing', 'parent': 'CELL_01'},
    {'name': 'exp_003.par', 'type': 'file', 'chemistry': None, 'capacity_ah': None, 'files': None, 'material': None,
     'status': '❌ Error', 'parent': 'CELL_01'},

    # File-level rows for CELL_02
    {'name': 'exp_004.par', 'type': 'file', 'chemistry': None, 'capacity_ah': None, 'files': None, 'material': None,
     'status': '✓ Processed', 'parent': 'CELL_02'},
    {'name': 'exp_005.par', 'type': 'file', 'chemistry': None, 'capacity_ah': None, 'files': None, 'material': None,
     'status': '✓ Processed', 'parent': 'CELL_02'},

    # File-level rows for CELL_03
    {'name': 'exp_006.par', 'type': 'file', 'chemistry': None, 'capacity_ah': None, 'files': None, 'material': None,
     'status': '✓ Processed', 'parent': 'CELL_03'},
    {'name': 'exp_007.par', 'type': 'file', 'chemistry': None, 'capacity_ah': None, 'files': None, 'material': None,
     'status': '⏳ Processing', 'parent': 'CELL_03'},
    {'name': 'exp_008.par', 'type': 'file', 'chemistry': None, 'capacity_ah': None, 'files': None, 'material': None,
     'status': '✓ Processed', 'parent': 'CELL_03'},
    {'name': 'exp_009.par', 'type': 'file', 'chemistry': None, 'capacity_ah': None, 'files': None, 'material': None,
     'status': '❌ Error', 'parent': 'CELL_03'},
]

df = pd.DataFrame(fake_data)

print("Data Preview:")
print(df.head(10))


# Test different Perspective configurations
def create_perspective_tests():
    """Create multiple Perspective configurations to test hierarchical capabilities."""

    # Test 1: Basic grouping by parent
    test1 = pn.pane.Perspective(
        df,
        group_by=['parent'],
        width=800,
        height=400,
        title="Test 1: Group by Parent"
    )

    # Test 2: Group by type (cell vs file)
    test2 = pn.pane.Perspective(
        df,
        group_by=['type'],
        width=800,
        height=400,
        title="Test 2: Group by Type"
    )

    # Test 3: Split by parent and type
    test3 = pn.pane.Perspective(
        df,
        group_by=['parent', 'type'],
        width=800,
        height=400,
        title="Test 3: Group by Parent + Type"
    )

    # Test 4: With row selection enabled
    test4 = pn.pane.Perspective(
        df,
        group_by=['parent'],
        selectable=True,
        width=800,
        height=400,
        title="Test 4: Group by Parent + Selection"
    )

    # Test 5: Alternative data structure - explicit hierarchy
    hierarchy_data = []
    for _, row in df.iterrows():
        if row['parent'] is None:
            # Cell rows get path like ['CELL_01']
            hierarchy_data.append({
                **row.to_dict(),
                'path': [row['name']]
            })
        else:
            # File rows get path like ['CELL_01', 'exp_001.par']
            hierarchy_data.append({
                **row.to_dict(),
                'path': [row['parent'], row['name']]
            })

    hierarchy_df = pd.DataFrame(hierarchy_data)

    test5 = pn.pane.Perspective(
        hierarchy_df,
        width=800,
        height=400,
        title="Test 5: Explicit Path Structure"
    )

    return pn.Column(
        "# Perspective Hierarchical Tests",
        "## Test Results:",
        "Look for:",
        "- ✅ Expandable rows (+ / - icons)",
        "- ✅ Individual row selection within groups",
        "- ✅ Click events on specific rows",
        "- ❌ If only flat tables with grouping headers",
        "",
        test1,
        test2,
        test3,
        test4,
        test5,
        width=900
    )


# Create selection callback test
def test_selection_callbacks():
    """Test if we can capture row selections."""

    selection_output = pn.pane.HTML("No selection yet...")

    def on_click(event):
        selection_output.object = f"""
        <div style='background: #e8f5e8; padding: 10px; border-radius: 4px;'>
            <strong>Selection Event:</strong><br>
            Row: {event.row}<br>
            Column Names: {event.column_names}<br>
            Config: {event.config}
        </div>
        """

    perspective_with_callback = pn.pane.Perspective(
        df,
        group_by=['parent'],
        selectable=True,
        width=800,
        height=300
    )

    # Try to add click callback
    try:
        perspective_with_callback.on_click(on_click)
        callback_status = "✅ Click callback registered successfully"
    except Exception as e:
        callback_status = f"❌ Click callback failed: {str(e)}"

    return pn.Column(
        "## Selection Callback Test:",
        callback_status,
        perspective_with_callback,
        "Selection Output:",
        selection_output,
        width=900
    )


# Create the complete test app
def create_test_app():
    return pn.Column(
        create_perspective_tests(),
        "---",
        test_selection_callbacks(),
        width=950
    )


# Create and serve the app
if __name__ == "__main__":
    # For testing in Jupyter or direct execution
    app = create_test_app()

    # To run as a server:
    # pn.serve(create_test_app, show=True, port=5007)

    app.show(port=8161)
else:
    # For importing
    app = create_test_app()