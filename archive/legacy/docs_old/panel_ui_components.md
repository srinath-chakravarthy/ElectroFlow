# Panel Web Interface - UI Components Documentation

## Overview

The Electrochemical Analysis Suite uses a modern Panel web interface with professional styling and responsive design. The interface provides a comprehensive solution for battery data analysis with clean visual hierarchy and intuitive workflows.

### Key Architecture Features

- **Card-based Design**: Clean, professional card layout with shadows and gradients
- **Responsive Layout**: 3-column layout that adapts to screen size  
- **Component Separation**: Modular design with clear responsibilities
- **Professional Styling**: Scientific color scheme with consistent branding
- **Real-time Updates**: Dynamic status updates and progress feedback

## Core Components

### 1. Main Application (`main_app.py`)

The `ElectrochemicalApp` class orchestrates the entire interface and provides the main application logic.

#### Key Features:
- **Professional CSS Styling**: Complete custom CSS with scientific color scheme
- **Component Connection**: Manages communication between all components
- **Status Management**: Centralized status system with timestamps
- **Layout Management**: 3-column responsive layout with fixed sidebars

#### Layout Structure:
```
┌─────────────────────────────────────────────────────────┐
│                    Header (Gradient Blue)              │
├─────────────────┬─────────────────┬─────────────────────┤
│   Cell Manager  │  File Uploader  │   Data Viewer       │
│   (350px fixed) │  (350px fixed)  │   (expandable)      │
│                 │                 │                     │
│  • Create cells │  • Upload files │  • Interactive     │
│  • Select cells │  • Process data │    plotting        │
│  • Manage cells │  • View files   │  • Data preview    │
└─────────────────┴─────────────────┴─────────────────────┤
│                    Status Bar                           │
└─────────────────────────────────────────────────────────┘
```

#### Styling Highlights:
- **Gradient Headers**: `linear-gradient(135deg, #2E4057 0%, #1976D2 100%)`
- **Status Colors**: Success (green), Warning (orange), Error (red), Info (blue)
- **Card Shadows**: `box-shadow: 0 2px 8px rgba(0,0,0,0.1)`
- **Hover Effects**: Enhanced shadows on hover for better interaction feedback

### 2. Cell Manager (`components/cell_manager.py`)

Comprehensive cell creation and management interface with detailed metadata collection.

#### Features:
- **Rich Cell Creation**: Multiple metadata fields (chemistry, capacity, electrode details)
- **Professional Form Layout**: Organized sections with proper labels and spacing  
- **Visual Cell List**: Shows chemistry type and file count for each cell
- **Selected Cell Feedback**: Clear visual indication of currently selected cell
- **Form Validation**: Input validation with user-friendly error messages

#### UI Sections:
1. **Create New Cell**: 
   - Basic info (name, chemistry, description)
   - Battery specifications (capacity)
   - Electrode details (cathode/anode materials and masses)
   - Notes field for observations

2. **Existing Cells**:
   - Formatted list with chemistry and file count
   - Select/refresh/delete operations
   - Visual selection feedback

#### Data Collected:
```python
{
    "name": "CELL_001",
    "chemistry": "Li_ion", 
    "description": "Formation cycles",
    "capacity_ah": 2.5,
    "cathode_material": "NMC811",
    "cathode_mass_mg": 15.2,
    "anode_material": "Li metal", 
    "anode_mass_mg": 0.0,
    "notes": "Temperature controlled formation"
}
```

### 3. File Uploader (`components/file_uploader.py`)

Step-by-step file processing workflow with clear visual guidance.

#### Features:
- **Dual File Upload**: Paired .par + .par.csv file handling
- **Current Cell Display**: Shows which cell files will be uploaded to
- **Temperature Setting**: Configurable processing temperature
- **Progress Feedback**: Real-time processing status updates
- **File Management**: View, select, and delete processed files

#### Workflow Steps:
1. **Cell Selection**: Must select cell before upload is enabled
2. **File Upload**: Upload both metadata (.par) and data (.par.csv) files
3. **Processing**: Files are parsed and stored with temperature metadata
4. **File Management**: View and manage processed files for the current cell

#### Visual States:
- **No Cell Selected**: Orange warning display
- **Cell Selected**: Green confirmation display  
- **Files Ready**: Blue "Process Files" button enabled
- **Processing**: Loading indicator with status updates
- **Complete**: Success message with file list refresh

### 4. Data Viewer (`components/data_viewer.py`)

Professional data visualization with intelligent plot type detection.

#### Features:
- **AC Data Detection**: Automatically detects impedance data for Nyquist plots
- **Dynamic Decimation**: Handles large datasets (>10k points) with HoloViews decimation
- **Plot Type Selection**: Dropdown with available plot types based on data
- **Data Preview**: Toggle-able data table (first 1000 rows)
- **Professional Styling**: Consistent color scheme and interactive tools

#### Supported Plot Types:
1. **Voltage vs Time**: Time series of potential measurements
2. **Current vs Time**: Time series of current measurements  
3. **Nyquist Plot**: Complex impedance plots (when AC data detected)
   - Automatic segment coloring for multiple EIS measurements
   - Proper -Z_imag convention for standard EIS visualization
   - Equal aspect ratio for accurate impedance circles

#### Plot Features:
- **Interactive Tools**: Pan, zoom, box zoom, reset, save
- **Dynamic Decimation**: Automatic point reduction for performance
- **Professional Colors**: Scientific blue (#1976D2) as primary color
- **Segment Coloring**: Different colors for multiple measurement segments

#### Data Processing:
```python
# Intelligent plot type detection
def _get_available_plot_types(self, data):
    options = []
    if 'potential_v' in data.columns:
        options.append("Voltage vs Time")
    if 'current_a' in data.columns:  
        options.append("Current vs Time")
    if self._has_impedance_data(data):
        options.append("Nyquist Plot")
    return options
```

### 5. Status Bar (`components/status_bar.py`)

Integrated status system with professional feedback and system information.

#### Features:
- **Real-time Updates**: Timestamps on all status messages
- **Professional Color Coding**: Consistent status type styling
- **System Information**: Shows technology stack information
- **Progress Support**: Optional progress bar for long operations
- **Clean Integration**: Seamless integration with main interface

#### Status Types:
- **Success**: Green with checkmark (✅)
- **Warning**: Orange with warning (⚠️)  
- **Error**: Red with X mark (❌)
- **Info**: Blue with info (ℹ️)
- **Processing**: Blue with spinner (🔄)

## Data Flow and Component Communication

### 1. Cell Selection Flow
```
Cell Manager (select) → Main App → File Uploader (enable upload)
                                → Data Viewer (clear plots)
```

### 2. File Processing Flow  
```
File Uploader (process) → Backend API → Database + Parquet
                       → Main App (status) → File Uploader (refresh list)
```

### 3. Data Visualization Flow
```
File Uploader (select file) → Main App → Data Viewer (load data)
                            → Backend API (get data) → Plot Generation
```

### 4. Status Updates Flow
```
Any Component (status change) → Main App (status handler) → Status Bar (display)
```

## Styling System

### Color Palette
- **Primary Blue**: `#1976D2` - Main brand color
- **Dark Blue**: `#2E4057` - Headers and emphasis  
- **Success Green**: `#2E7D32` - Success states
- **Warning Orange**: `#F57C00` - Warnings and alerts
- **Error Red**: `#D32F2F` - Error states
- **Light Gray**: `#F8F9FA` - Background color
- **Card White**: `#FFFFFF` - Card backgrounds

### Typography
- **Font Family**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`
- **Header Sizes**: 18px (component headers), 16px (section headers), 14px (labels)
- **Font Weights**: 600 (headers), 500 (labels), 400 (body)

### Card Design
```css
.card-container {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin: 10px;
    overflow: hidden;
    transition: box-shadow 0.3s ease;
}
```

## Technical Implementation

### Panel Configuration
- **Sizing Mode**: `stretch_width` for responsive layout
- **HoloViews Integration**: Professional plotting with Bokeh backend
- **Dynamic Updates**: Param watchers for reactive interfaces
- **Memory Efficiency**: Data decimation for large datasets

### Performance Optimizations
- **Lazy Loading**: Data loaded only when needed
- **Decimation**: Automatic point reduction for large datasets (>10k points)
- **Efficient Updates**: Targeted UI updates instead of full refreshes
- **Memory Management**: Proper cleanup of plot objects

### Browser Compatibility
- **Modern Browsers**: Chrome, Firefox, Safari, Edge
- **Responsive Design**: Works on desktop and tablet devices
- **Touch Support**: Pan and zoom work with touch interfaces

## Configuration and Customization

### Environment Variables (.env)
```env
WEB_PORT=5007              # Web server port
WEB_HOST=localhost         # Web server host
WEB_DEBUG=False           # Debug mode
LOG_LEVEL=INFO            # Logging level
```

### Styling Customization
The main CSS is embedded in `main_app.py` and can be customized:
- Colors in the palette section
- Card styling and shadows
- Button appearances and hover effects
- Status bar layouts and colors

### Component Extension
Each component is designed for easy extension:
- Add new plot types in `DataViewer._get_available_plot_types()`
- Add cell metadata fields in `CellFileManagement._create_components()`
- Add status types in `StatusBar.status_configs`

## Usage Examples

### Launching the Interface
```bash
# Command line
python echem_web.py --port 5007

# With development features
python echem_web.py --port 5007 --dev

# Using configuration
# Will use port from .env file
python echem_web.py
```

### Accessing the Interface
- Open browser to `http://localhost:5007`
- Interface loads with welcome screen
- Create or select cell to begin
- Upload .par + .par.csv files
- View interactive plots and data

## Development and Maintenance

### Code Organization
```
src_clean/panel_app/
├── main_app.py              # Main application orchestration
├── components/
│   ├── cell_manager.py      # Cell creation and management
│   ├── file_uploader.py     # File upload and processing
│   ├── data_viewer.py       # Data visualization and plotting  
│   └── status_bar.py        # Status display and feedback
└── __init__.py
```

### Best Practices
1. **Component Isolation**: Each component manages its own state
2. **Clear Interfaces**: Well-defined parameter communication
3. **Error Handling**: Graceful error display with user-friendly messages
4. **Responsive Design**: Layout adapts to different screen sizes
5. **Professional Appearance**: Consistent styling and visual hierarchy

The Panel interface represents a significant improvement over the previous Qt-based interface, providing better web compatibility, responsive design, and professional appearance suitable for scientific applications.