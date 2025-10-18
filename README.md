# Graphical Monitor for OpenFOAM.<br>
Features:

### **📊 Real-Time Monitoring**
- **Live plotting** of OpenFOAM simulation data
- **Automatic file discovery** in `postProcessing/` directory
- **Multiple data types support**:
  - Residuals (convergence monitoring)
  - Probe data (pressure, velocity, temperature)
  - XY plots
  - Generic time-series data

### **⚙️ Configurable Refresh Rates**
- **5 interval options**: 1, 2, 5, 10, 30 seconds
- **Runtime switching** - change intervals without restart
- **Terminal feedback** when intervals change
- **Status bar display** of current refresh rate

### **🔊 Output Control**
- **Verbose toggle** - control terminal output
- **File read notifications** (when verbose enabled)
- **Error reporting** (when verbose enabled)
- **Interval change announcements**

Screenshots:
<img width="1335" height="421" alt="image" src="https://github.com/user-attachments/assets/00ff83e7-fc6e-4d0f-b3d1-e41123482a84" />
<br>
<br>

Run from the OpenFOAM case directory. E.g.:<br>

```bash
python3 ~/OpenFOAM/foamMonitor.py
```
Or graphically select case directory:<br>
<img width="240" height="165" alt="image" src="https://github.com/user-attachments/assets/f81c8fa1-27c1-4316-8bf8-b304a0eb39bf" />
<br>
<br>
Prerequisites:
- matplotlib
- pandas

<br>
💡 See "function" file (place in system directory) for example entries for monitored quantities.<br>
<br>
Tested with OpenFOAM 12.

