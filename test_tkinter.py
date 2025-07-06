import tkinter as tk
from tkinter import ttk, messagebox

root = tk.Tk()
root.title("Tkinter Test")
label = ttk.Label(root, text="Tkinter is working!")
label.pack(pady=20)
root.mainloop()
