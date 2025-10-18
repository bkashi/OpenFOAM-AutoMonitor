import tkinter as tk
from subprocess import run
from os import getcwd, walk
from os.path import join, basename, dirname
from glob import glob
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from pandas import read_csv
from tkinter import filedialog
from functools import lru_cache
from typing import List, Optional, Callable

# Constants
DEFAULT_UPDATE_INTERVAL = 1000  # ms
WINDOW_SIZE = "600x500"
FIGURE_SIZE = (18, 14)
DPI = 100
FIGURE_COLOR = 'lightgrey'

# Refresh interval options (seconds)
REFRESH_INTERVALS = [1, 2, 5, 10, 30]

# Menu configuration
MENU_ITEMS = [
    ('Open', 'select_case_dir'),
    ('Refresh', 'refresh_monitor_paths'),
    ('Stop', 'stop_solver'),
    ('Quit', 'quit_app')
]


class FoamMonitor:
    """Optimized OpenFOAM monitoring tool with real-time plotting."""
    
    def __init__(self):
        self.cwd = getcwd()
        self.monitor_paths: List[str] = []
        self.active_monitor = 0
        self.root = None
        self.listbox = None
        self.fig = None
        self.plt = None
        self.fig_canvas = None
        self.anim = None
        self.update_interval = DEFAULT_UPDATE_INTERVAL  # Current interval in ms
        self.status_bar = None
        self.verbose = True  # Verbose output toggle
        
        self._setup_gui()
        self._initialize_monitoring()
    
    def _setup_gui(self):
        """Initialize the GUI components."""
        self.root = tk.Tk()
        self.root.geometry(WINDOW_SIZE)
        self.root.title("AutoFoamMonitor")
        self.root.bind("<q>", lambda x: self.root.quit())
        self.root.bind("<r>", lambda x: self.refresh_monitor_paths())
        
        # Create menu
        menubar = self._create_menu()
        self.root.config(menu=menubar)
        
        # Create listbox frame
        self._create_listbox_frame()
        
        # Create status bar (pack this before the expanding plot frame)
        self._create_status_bar()
        
        # Create plot frame (this will expand to fill remaining space)
        self._create_plot_frame()
    
    def _create_menu(self) -> tk.Menu:
        """Create the menu bar."""
        menubar = tk.Menu(self.root)
        
        # Actions menu
        actions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="⚡ Actions", menu=actions_menu)
        actions_menu.add_command(label="📁 Open Case Directory", command=self.select_case_dir)
        actions_menu.add_command(label="🔄 Refresh File List", command=self.refresh_monitor_paths)
        actions_menu.add_command(label="⏹ Stop Solver", command=self.stop_solver)
        actions_menu.add_separator()
        actions_menu.add_command(label="❌ Quit", command=self.quit_app)
        
        # Options menu
        options_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="⚙️ Options", menu=options_menu)
        
        # Refresh interval submenu
        interval_menu = tk.Menu(options_menu, tearoff=0)
        options_menu.add_cascade(label="⏱️ Refresh Interval", menu=interval_menu)
        
        for interval in REFRESH_INTERVALS:
            interval_menu.add_command(
                label=f"⏰ {interval} second{'s' if interval != 1 else ''}",
                command=lambda i=interval: self.set_refresh_interval(i)
            )
        
        # Verbose output toggle
        options_menu.add_separator()
        options_menu.add_command(label="🔊 Toggle Verbose Output", command=self.toggle_verbose)
        
        return menubar
    
    def _create_listbox_frame(self):
        """Create the listbox for file selection."""
        frame1 = tk.Frame(self.root)
        scrollbar = tk.Scrollbar(frame1, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(frame1, yscrollcommand=scrollbar.set, 
                                 width=60, height=4, bd=6, font='13')
        self.listbox.bind('<<ListboxSelect>>', self._onselect)
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(fill=tk.BOTH)
        frame1.pack(fill=tk.BOTH)
    
    def _create_plot_frame(self):
        """Create the matplotlib plotting frame."""
        frame2 = tk.Frame(self.root)
        canvas = tk.Canvas(frame2)
        canvas.pack(fill=tk.BOTH)
        frame2.pack(fill=tk.BOTH)
        
        self.fig = Figure(figsize=FIGURE_SIZE, dpi=DPI, facecolor=FIGURE_COLOR)
        self.plt = self.fig.add_subplot(111, facecolor=FIGURE_COLOR)
        self.fig_canvas = FigureCanvasTkAgg(self.fig, master=canvas)
        self.fig_canvas.draw()
        self.fig_canvas.get_tk_widget().pack()
    
    def _create_status_bar(self):
        """Create status bar at the bottom of the window."""
        self.status_bar = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # Status text
        self.status_text = tk.Label(self.status_bar, text="", anchor=tk.W)
        self.status_text.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Update status with initial information
        self._update_status()
    
    def _update_status(self):
        """Update the status bar with current information."""
        interval_seconds = self.update_interval // 1000
        status = f"Case: {self.cwd} | Refresh: {interval_seconds}s"
        self.status_text.config(text=status)
    
    def _initialize_monitoring(self):
        """Initialize monitoring paths and start animation."""
        self.refresh_monitor_paths()
        self.anim = FuncAnimation(self.fig, self._update_plot, interval=self.update_interval, repeat=True)
    
    def refresh_monitor_paths(self):
        """Refresh the list of monitoring files using Python instead of shell commands."""
        self.monitor_paths = []
        postprocessing_dir = join(self.cwd, 'postProcessing')
        
        try:
            for root, dirs, files in walk(postprocessing_dir):
                for file in files:
                    self.monitor_paths.append(join(root, file))
        except FileNotFoundError:
            self.monitor_paths = []
        
        # Update listbox
        self.listbox.delete(0, tk.END)
        for path in self.monitor_paths:
            # Show last 4 path components for readability
            display_path = '/'.join(path.split('/')[-4:])
            self.listbox.insert(tk.END, display_path)
    
    @lru_cache(maxsize=32)
    def _read_monitor_file(self, filepath: str, **kwargs) -> Optional[object]:
        """Cached file reading to avoid repeated I/O."""
        try:
            return read_csv(filepath, **kwargs)
        except Exception:
            return None
    
    def _get_plot_handler(self, filename: str) -> Callable:
        """Get the appropriate plotting function based on file type."""
        if filename.endswith(('p', 'U', 'T')):
            return self._plot_probes
        elif filename == 'residuals.dat':
            return self._plot_residuals
        elif filename.endswith('.xy'):
            return self._plot_xy
        else:
            return self._plot_generic
    
    def _plot_probes(self, filepath: str):
        """Plot probe data (pressure, velocity, temperature)."""
        self.plt.set_yscale('linear')
        self.plt.set_xlabel('Time [s]')
        
        df = self._read_monitor_file(filepath, delim_whitespace=True, 
                                   header=None, skiprows=3)
        if df is None:
            return
        
        # Get probe information
        probe_info = self._get_probe_info(filepath)
        n_probes = probe_info['count']
        probe_names = probe_info['names']
        
        columns = list(df.columns)[1:]
        
        if filepath.endswith('U'):
            self._plot_velocity_magnitude(df, columns, probe_names, n_probes)
        else:
            self._plot_scalar_probes(df, columns, probe_names, filepath)
        
        self.plt.legend()
    
    def _get_probe_info(self, filepath: str) -> dict:
        """Get probe count and names from file."""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            probe_lines = [line for line in lines if 'Probe' in line]
            return {
                'count': len(probe_lines),
                'names': [line.strip() for line in probe_lines]
            }
        except Exception:
            return {'count': 0, 'names': []}
    
    def _plot_velocity_magnitude(self, df, columns, probe_names, n_probes):
        """Plot velocity magnitude for each probe."""
        self.plt.set_ylabel('Speed [m/s]')
        
        for probe in range(n_probes):
            n = probe * 3 + 1
            if n + 2 < len(columns):
                x = df[n].str.replace('(', '', regex=True).astype(float)
                y = df[n + 1].astype(float)
                z = df[n + 2].str.replace(')', '', regex=True).astype(float)
                magnitude = np.sqrt(x**2 + y**2 + z**2)
                
                label = probe_names[probe] if probe < len(probe_names) else f'Probe {probe}'
                self.plt.plot(magnitude, label=label)
    
    def _plot_scalar_probes(self, df, columns, probe_names, filepath):
        """Plot scalar probe data (pressure, temperature)."""
        for probe, column in enumerate(columns):
            label = probe_names[probe] if probe < len(probe_names) else f'Probe {probe}'
            self.plt.plot(df[column], label=label)
        
        if filepath.endswith('p'):
            self.plt.set_ylabel('Pressure [Pa]')
        elif filepath.endswith('T'):
            self.plt.set_ylabel('Temperature [K]')
        else:
            self.plt.set_ylabel('')
    
    def _plot_residuals(self, filepath: str):
        """Plot convergence residuals."""
        self.plt.set_yscale('log')
        self.plt.set_xlabel('Iteration')
        self.plt.set_ylabel('Residual')
        
        df = self._read_monitor_file(filepath, sep='\t', header=1, lineterminator='\n')
        if df is None:
            return
        
        columns = list(df.columns)[1:]
        for column in columns:
            curr_val = float(df[column].tail(1))
            self.plt.plot(df[column], label=f'{column}({curr_val:.1e})')
        
        self.plt.legend()
    
    def _plot_xy(self, filepath: str):
        """Plot XY data."""
        self.plt.set_yscale('linear')
        self.plt.set_xlabel('Point')
        
        df = self._read_monitor_file(filepath, delim_whitespace=True)
        if df is None:
            return
        
        columns = list(df.columns)
        for column in columns[2:]:
            self.plt.plot(df[column], label=column)
        
        self.plt.legend()
    
    def _plot_generic(self, filepath: str):
        """Plot generic time-series data."""
        self.plt.set_yscale('linear')
        self.plt.set_xlabel('Time [s]')
        
        df = self._read_monitor_file(filepath, delim_whitespace=True, skiprows=3)
        if df is None:
            return
        
        columns = list(df.columns)
        if len(columns) > 1:
            self.plt.plot(df[columns[1]])
            self.plt.set_ylabel(columns[2] if len(columns) > 2 else '')
            curr_val = float(df[columns[1]].tail(1))
            self.plt.set_title(f'Current value: {curr_val}')
    
    def _update_plot(self, frame):
        """Update the plot with current data."""
        self.plt.clear()
        
        if not self.monitor_paths:
            return
        
        try:
            active_monitor_path = self.monitor_paths[self.active_monitor]
            filename = basename(active_monitor_path)
            
            # Announce file being read
            if self.verbose:
                print(f"Reading data from: {filename}")
            
            plot_handler = self._get_plot_handler(filename)
            plot_handler(active_monitor_path)
            
            self.fig.canvas.draw()
        except (IndexError, Exception) as e:
            # Handle errors gracefully
            if self.verbose:
                print(f"Error reading file: {str(e)}")
            self.plt.text(0.5, 0.5, f'Error: {str(e)}', 
                         transform=self.plt.transAxes, ha='center')
            self.fig.canvas.draw()
    
    def _onselect(self, selection):
        """Handle listbox selection events."""
        try:
            self.active_monitor = self.listbox.curselection()[0]
            self._update_plot(1)
        except IndexError:
            pass  # No selection made
    
    def select_case_dir(self):
        """Select a new OpenFOAM case directory."""
        new_cwd = filedialog.askdirectory(initialdir=self.cwd, 
                                        title="Select OpenFOAM Case Directory")
        if new_cwd:
            self.cwd = new_cwd
            self.refresh_monitor_paths()
            self._update_status()
    
    def stop_solver(self):
        """Stop the foamRun solver process."""
        try:
            run(['notify-send', 'foamRun stopped'], check=False)
            run(['pkill', 'foamRun'], check=False)
        except Exception:
            pass  # Handle errors gracefully
    
    def set_refresh_interval(self, interval_seconds: int):
        """Set the refresh interval in seconds."""
        self.update_interval = interval_seconds * 1000  # Convert to milliseconds
        
        # Stop current animation
        if self.anim:
            self.anim.event_source.stop()
            self.anim = None
        
        # Start new animation with new interval
        self.anim = FuncAnimation(self.fig, self._update_plot, interval=self.update_interval, repeat=True)
        
        # Update status bar with new interval
        self._update_status()
        
        # Announce interval change to terminal
        if self.verbose:
            print(f"Refresh interval updated to {interval_seconds} second{'s' if interval_seconds != 1 else ''}")
        
        # Force an immediate update to ensure continuity
        self._update_plot(0)
    
    def toggle_verbose(self):
        """Toggle verbose output on/off."""
        self.verbose = not self.verbose
        status = "enabled" if self.verbose else "disabled"
        print(f"Verbose output {status}")
    
    def quit_app(self):
        """Quit the application."""
        self.root.quit()
    
    def run(self):
        """Start the monitoring application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    monitor = FoamMonitor()
    monitor.run()


if __name__ == '__main__':
    main()
