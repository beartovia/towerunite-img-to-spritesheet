import cv2
import numpy as np
from PIL import Image
import os
import math
from pathlib import Path
import ffmpeg
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import io

class SpriteSheetGenerator:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Sprite Sheet Generator")
        self.setup_ui()
        
    def setup_ui(self):
        # File selection
        tk.Button(self.window, text="Select File", command=self.select_file).pack(pady=5)
        
        # Frame info frame
        info_frame = ttk.LabelFrame(self.window, text="Frame Information")
        info_frame.pack(padx=5, pady=5, fill="x")
        
        self.frame_count_var = tk.StringVar(value="Total Frames: -")
        tk.Label(info_frame, textvariable=self.frame_count_var).pack()
        
        self.suggested_layout_var = tk.StringVar(value="Suggested Layout: -")
        tk.Label(info_frame, textvariable=self.suggested_layout_var).pack()
        
        # Layout frame
        layout_frame = ttk.LabelFrame(self.window, text="Layout Settings")
        layout_frame.pack(padx=5, pady=5, fill="x")
        
        # Radio buttons for layout choice
        self.layout_choice = tk.StringVar(value="auto")
        tk.Radiobutton(layout_frame, text="Auto-optimize layout", 
                      variable=self.layout_choice, 
                      value="auto",
                      command=self.toggle_layout_inputs).pack()
        tk.Radiobutton(layout_frame, text="Manual layout", 
                      variable=self.layout_choice,
                      value="manual",
                      command=self.toggle_layout_inputs).pack()
        
        # Manual layout inputs
        self.manual_frame = ttk.Frame(layout_frame)
        self.manual_frame.pack(fill="x", padx=5)
        
        tk.Label(self.manual_frame, text="Rows:").pack(side=tk.LEFT)
        self.rows_var = tk.StringVar()
        self.rows_entry = tk.Entry(self.manual_frame, textvariable=self.rows_var, width=10)
        self.rows_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.manual_frame, text="Columns:").pack(side=tk.LEFT)
        self.cols_var = tk.StringVar()
        self.cols_entry = tk.Entry(self.manual_frame, textvariable=self.cols_var, width=10)
        self.cols_entry.pack(side=tk.LEFT, padx=5)
        
        # Output settings frame
        settings_frame = ttk.LabelFrame(self.window, text="Output Settings")
        settings_frame.pack(padx=5, pady=5, fill="x")
        
        tk.Label(settings_frame, text="Quality (1-100):").pack()
        self.quality_var = tk.IntVar(value=85)
        tk.Scale(settings_frame, from_=1, to=100, orient="horizontal", 
                variable=self.quality_var).pack()
        
        tk.Label(settings_frame, text="Colors (2-256):").pack()
        self.colors_var = tk.IntVar(value=256)
        tk.Scale(settings_frame, from_=2, to=256, orient="horizontal", 
                variable=self.colors_var).pack()
        
        # Generate button
        tk.Button(self.window, text="Generate Sprite Sheet", 
                 command=self.generate_sprite_sheet).pack(pady=10)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.window, textvariable=self.status_var).pack()
        
        # Initially disable manual inputs
        self.toggle_layout_inputs()

    def toggle_layout_inputs(self):
        is_manual = self.layout_choice.get() == "manual"
        state = 'normal' if is_manual else 'disabled'
        self.rows_entry.configure(state=state)
        self.cols_entry.configure(state=state)

    def find_optimal_factors(self, n):
        """Find the most suitable factors for the frame count"""
        # Get all factors
        factors = []
        for i in range(1, int(math.sqrt(n)) + 1):
            if n % i == 0:
                factors.append(i)
                if i != n // i:
                    factors.append(n // i)
        factors.sort()
        
        # Find the pair of factors closest to a square
        best_ratio = float('inf')
        best_pair = (1, n)
        
        for rows in factors:
            cols = n // rows
            # Prefer wider layouts (more columns than rows)
            ratio = abs(cols / rows - 1.5)  # Aim for roughly 1.5:1 aspect ratio
            if ratio < best_ratio:
                best_ratio = ratio
                best_pair = (rows, cols)
        
        return best_pair

    def get_prime_adjusted_frame_count(self, n):
        """Adjust frame count if it's prime or hard to factor"""
        if n < 2:
            return n
            
        # Check if number is prime
        for i in range(2, int(math.sqrt(n)) + 1):
            if n % i == 0:
                return n
                
        # If prime, subtract 1 to get a more factorizable number
        return n - 1

    def select_file(self):
        filetypes = (
            ('Video files', '*.mp4;*.avi;*.mov'),
            ('GIF files', '*.gif'),
            ('WebP files', '*.webp'),
            ('All files', '*.*')
        )
        self.filename = filedialog.askopenfilename(filetypes=filetypes)
        if self.filename:
            # Extract frames to get count
            self.frames = self.extract_frames(self.filename)
            frame_count = len(self.frames)
            
            # Update frame count display
            self.frame_count_var.set(f"Total Frames: {frame_count}")
            
            # Calculate and display suggested layout
            adjusted_count = self.get_prime_adjusted_frame_count(frame_count)
            rows, cols = self.find_optimal_factors(adjusted_count)
            self.suggested_layout_var.set(f"Suggested Layout: {rows}x{cols}")
            
            # Update status
            self.status_var.set(f"Selected: {Path(self.filename).name}")
            
            # Pre-fill manual inputs with suggested values
            self.rows_var.set(str(rows))
            self.cols_var.set(str(cols))

    def extract_frames(self, file_path):
        frames = []
        
        if file_path.lower().endswith(('.gif', '.webp')):
            img = Image.open(file_path)
            for frame in range(getattr(img, 'n_frames', 1)):
                img.seek(frame)
                frames.append(np.array(img.convert('RGB')))
        else:
            cap = cv2.VideoCapture(file_path)
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            cap.release()
            
        return frames

    def generate_sprite_sheet(self):
        if not hasattr(self, 'filename') or not hasattr(self, 'frames'):
            messagebox.showerror("Error", "Please select a file first!")
            return
            
        self.status_var.set("Processing...")
        
        frame_count = len(self.frames)
        
        # Get layout settings
        if self.layout_choice.get() == "auto":
            adjusted_count = self.get_prime_adjusted_frame_count(frame_count)
            rows, cols = self.find_optimal_factors(adjusted_count)
        else:
            try:
                rows = int(self.rows_var.get())
                cols = int(self.cols_var.get())
                if rows <= 0 or cols <= 0:
                    raise ValueError
                if rows * cols < frame_count:
                    messagebox.showerror("Error", 
                        f"Layout {rows}x{cols} is too small for {frame_count} frames!")
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid row/column values!")
                return
        
        # Create sprite sheet
        frame_height, frame_width = self.frames[0].shape[:2]
        sprite_sheet = np.zeros((frame_height * rows, frame_width * cols, 3), 
                              dtype=np.uint8)
        
        # Fill sprite sheet
        for idx, frame in enumerate(self.frames):
            if idx >= rows * cols:  # Skip extra frames
                break
            i, j = idx // cols, idx % cols
            sprite_sheet[i * frame_height:(i + 1) * frame_height,
                        j * frame_width:(j + 1) * frame_width] = frame
        
        # Convert to PIL Image for optimization
        sprite_sheet_img = Image.fromarray(sprite_sheet)
        
        # Reduce colors if specified
        if self.colors_var.get() < 256:
            sprite_sheet_img = sprite_sheet_img.quantize(
                colors=self.colors_var.get()).convert('RGB')
        
        # Save optimized sprite sheet
        output_path = Path(self.filename).with_name(
            f"{Path(self.filename).stem}_sprite_{rows}x{cols}.jpg")
        
        sprite_sheet_img.save(
            output_path,
            quality=self.quality_var.get(),
            optimize=True
        )
        
        self.status_var.set(f"Saved sprite sheet to: {output_path}")
        messagebox.showinfo("Success", 
            f"Sprite sheet generated with {rows}x{cols} layout!")

if __name__ == "__main__":
    app = SpriteSheetGenerator()
    app.window.mainloop()