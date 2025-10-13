import tkinter as tk
from subprocess import run
from os import getcwd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from pandas import read_csv
from tkinter import filedialog



def refresh_monitor_paths():
	global monitor_paths
	monitor_paths = run([f"find {cwd}/postProcessing/ -type f -name '*'"], shell=True, capture_output=True, text=True).stdout.split('\n')[0:-1]
	listbox.delete(0,999)
	for item in monitor_paths:
		listbox.insert(tk.END, item.split('/')[-4:])


def update_plot(frame):
	
	global monitor_paths
	
	plt.clear()

	if len(monitor_paths) > 0:
		active_monitor_path = monitor_paths[active_monitor]

		# probes
		if monitor_paths[active_monitor][-1] in ['p', 'U', 'T']:
			plt.set_yscale('linear')
			plt.set_xlabel('Time [s]')
			df = read_csv(active_monitor_path, delim_whitespace=True, header=None, skiprows=3)
			n_probes = int( run([f"grep 'Probe' {active_monitor_path} | wc -l"], shell=True, capture_output=True, text=True).stdout )
			probes = run([f"grep 'Probe' {active_monitor_path}"], shell=True, capture_output=True, text=True).stdout
			probes = probes.split('\n')
			columns = list(df.columns)[1:]
			if active_monitor_path[-1] == 'U':
				for probe in range(n_probes):
					n = probe*3 + 1
					df[n] = df[n].str.replace('(', '', regex=True).astype(float)  # remove '('
					df[n+2] = df[n+2].str.replace(')', '', regex=True).astype(float)  # remove ')'
					plt.plot((df[n]**2 + df[n+1]**2 + df[n+2]**2)**0.5, label=probes[probe])
					plt.set_ylabel('Speed [m/s]')
			else:
				for probe,column in enumerate(columns):
					plt.plot(df[column], label=probes[probe])
				if active_monitor_path[-1] == 'p':
					plt.set_ylabel('Pressure [Pa]')
				elif active_monitor_path[-1] == 'T':
					plt.set_ylabel('Temperature [K]')
				else:
					plt.set_ylabel('')
			plt.legend()

		# residuals
		elif monitor_paths[active_monitor].split('/')[-1] == 'residuals.dat':
			plt.set_yscale('log')
			plt.set_xlabel('Iteration')
			plt.set_ylabel('Residual')
			df = read_csv(active_monitor_path, sep='\t', header=1, lineterminator='\n')
			columns = list(df.columns)[1:]
			for i,column in enumerate(columns):
				curr_val = float(df[columns[i]].tail(1))
				plt.plot(df[column], label=f'{column}({curr_val:.1e})')
			plt.legend()

		# xy plots
		elif '.xy' in monitor_paths[active_monitor][-3:]:
			plt.set_yscale('linear')
			plt.set_xlabel('Point')
			df = read_csv(active_monitor_path, delim_whitespace=True)
			columns = list(df.columns)
			for column in columns[2:]:
				plt.plot(df[column], label=column)
			plt.legend()

		# other
		else:
			plt.set_yscale('linear')
			plt.set_xlabel('Time [s]')
			df = read_csv(active_monitor_path, delim_whitespace=True, skiprows=3)
			columns = list(df.columns)
			plt.plot(df[columns[1]])
			plt.set_ylabel(columns[2])
			curr_val = float(df[columns[1]].tail(1))
			plt.set_title(f'Current value: {curr_val}')
			
		fig.canvas.draw()


def onselect(selection):
	global active_monitor
	try:
		active_monitor = listbox.curselection()[0]
		update_plot(1)
	except:
		pass
	

def select_case_dir():
	global cwd
	cwd = filedialog.askdirectory(initialdir=cwd, title = "Select a File")
	refresh_monitor_paths()
	root.title(f"OpenFOAM Monitor [{cwd}]")


def stop_solver():
    run([f'notify-send "foamRun stopped"'], shell=True)
    run(['pkill foamRun'], shell=True)

if __name__ == '__main__':

	cwd = getcwd()
	monitor_paths = run([f"find {cwd}/postProcessing/ -type f -name '*'"],
							shell=True, capture_output=True, text=True).stdout.split('\n')[0:-1]

	root = tk.Tk()
	root.geometry("600x500")
	root.title(f"OpenFOAM Monitor [{cwd}]")
	root.bind("<q>", lambda x: quit())
	root.bind("<r>", lambda x: refresh_monitor_paths())
	
	menubar = tk.Menu(root)
	menubar.add_command(label='Open', command=select_case_dir)
	menubar.add_command(label='Refrsh', command=refresh_monitor_paths)
	menubar.add_command(label='Stop', command=stop_solver)
	menubar.add_command(label='Quit', command=exit)

	frame1 = tk.Frame(root)
	scrollbar = tk.Scrollbar(frame1, orient=tk.VERTICAL)
	listbox = tk.Listbox(frame1, yscrollcommand=scrollbar.set, width=60, height=4, bd=6, font='13')
	listbox.bind('<<ListboxSelect>>', onselect)
	scrollbar.config(command=listbox.yview)
	scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
	listbox.pack(fill=tk.BOTH)
	frame1.pack(fill=tk.BOTH)

	for item in monitor_paths:
		listbox.insert(tk.END, item.split('/')[-4:])
	active_monitor = 0

	frame2 = tk.Frame(root)
	canvas = tk.Canvas(frame2)
	canvas.pack(fill=tk.BOTH)
	frame2.pack(fill=tk.BOTH)

	fig = Figure(figsize = (18, 14), dpi = 100, facecolor='lightgrey')
	plt = fig.add_subplot(111,facecolor='lightgrey')
	fig_canvas = FigureCanvasTkAgg(fig, master=canvas)
	fig_canvas.draw()
	fig_canvas.get_tk_widget().pack() 

	anim = FuncAnimation(fig, update_plot, interval=2000)
	root.config(menu=menubar)

	root.mainloop()

