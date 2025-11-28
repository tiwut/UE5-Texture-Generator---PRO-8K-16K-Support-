import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageFilter
import numpy as np
import threading
import time

Image.MAX_IMAGE_PIXELS = None 

class TextureGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UE5 Texture Generator - PRO (8K/16K Support)")
        self.root.geometry("1100x850")
        self.root.configure(bg="#1e1e1e")

        self.generated_maps = {}
        self.preview_image = None
        self.is_generating = False

        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#2b2b2b")
        style.configure("TLabel", background="#2b2b2b", foreground="#dddddd", font=("Segoe UI", 9))
        style.configure("TButton", background="#444444", foreground="white", borderwidth=0)
        style.map("TButton", background=[("active", "#555555")])
        style.configure("Horizontal.TProgressbar", background="#007acc", troughcolor="#333333")
        main_container = tk.Frame(self.root, bg="#1e1e1e")
        main_container.pack(fill=tk.BOTH, expand=True)
        sidebar = tk.Frame(main_container, bg="#2b2b2b", width=320, padx=15, pady=15)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        preview_area = tk.Frame(main_container, bg="#1e1e1e")
        preview_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(sidebar, text="Texture Settings", font=("Segoe UI", 16, "bold"), bg="#2b2b2b", fg="white").pack(pady=(0, 15))
        self.create_label(sidebar, "Material Type:")
        self.type_var = tk.StringVar(value="Grass")
        ttk.Combobox(sidebar, textvariable=self.type_var, values=["Grass", "Dirt/Ground"], state="readonly").pack(fill=tk.X, pady=5)
        self.create_label(sidebar, "Resolution (Warning: 8K/16K uses high RAM):")
        self.res_var = tk.IntVar(value=1024)
        ttk.Combobox(sidebar, textvariable=self.res_var, values=[1024, 2048, 4096, 8192, 16384], state="readonly").pack(fill=tk.X, pady=5)
        self.create_separator(sidebar)
        tk.Label(sidebar, text="Surface Details", font=("Segoe UI", 11, "bold"), bg="#2b2b2b", fg="#4ca6ff").pack(anchor="w", pady=5)
        self.create_label(sidebar, "Noise Scale (Pattern Size):")
        self.scale_var = tk.DoubleVar(value=60.0)
        ttk.Scale(sidebar, from_=20.0, to=200.0, variable=self.scale_var).pack(fill=tk.X)
        self.create_label(sidebar, "Detail Octaves (Crispness/Layers):")
        self.octaves_var = tk.IntVar(value=3)
        ttk.Scale(sidebar, from_=1, to=6, variable=self.octaves_var, command=lambda x: self.octaves_var.set(int(float(x)))).pack(fill=tk.X)
        self.create_label(sidebar, "Density (Blade/Rock Count):")
        self.density_var = tk.DoubleVar(value=0.6)
        ttk.Scale(sidebar, from_=0.1, to=1.0, variable=self.density_var).pack(fill=tk.X)
        self.create_separator(sidebar)
        tk.Label(sidebar, text="Material Properties", font=("Segoe UI", 11, "bold"), bg="#2b2b2b", fg="#4ca6ff").pack(anchor="w", pady=5)

        self.create_label(sidebar, "Color Variation (Mix Strength):")
        self.color_var = tk.DoubleVar(value=0.5)
        ttk.Scale(sidebar, from_=0.0, to=1.0, variable=self.color_var).pack(fill=tk.X)

        self.create_label(sidebar, "Normal Map Intensity (Bump Depth):")
        self.normal_str_var = tk.DoubleVar(value=5.0)
        ttk.Scale(sidebar, from_=1.0, to=20.0, variable=self.normal_str_var).pack(fill=tk.X)

        self.create_separator(sidebar)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(sidebar, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(10, 5))
        
        self.status_label = tk.Label(sidebar, text="Ready", bg="#2b2b2b", fg="#888888", font=("Segoe UI", 8))
        self.status_label.pack(pady=2)

        self.btn_gen = tk.Button(sidebar, text="GENERATE TEXTURE", bg="#007acc", fg="white", font=("Segoe UI", 11, "bold"), height=2, command=self.start_generation)
        self.btn_gen.pack(fill=tk.X, pady=10)

        self.btn_save = tk.Button(sidebar, text="EXPORT TEXTURES", bg="#28a745", fg="white", font=("Segoe UI", 10, "bold"), height=1, command=self.save_textures)
        self.btn_save.pack(fill=tk.X, pady=5)
        tk.Label(preview_area, text="Preview (Scaled Down)", bg="#1e1e1e", fg="#555555").pack(pady=10)
        self.canvas = tk.Canvas(preview_area, width=600, height=600, bg="black", highlightthickness=0)
        self.canvas.pack(anchor="center", expand=True)

    def create_label(self, parent, text):
        tk.Label(parent, text=text, bg="#2b2b2b", fg="#cccccc").pack(anchor="w", pady=(10, 0))

    def create_separator(self, parent):
        tk.Frame(parent, height=1, bg="#444444").pack(fill=tk.X, pady=15)

    def generate_layered_noise(self, size, base_scale, octaves):
        """
        Creates high-quality Fractal Noise (FBM).
        Instead of one blurry layer, we stack multiple layers at different scales.
        """
        final_map = np.zeros((size, size), dtype=np.float32)
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for i in range(octaves):
            self.update_status(f"Generating Octave {i+1}/{octaves}...")
            current_scale = base_scale / frequency
            low_res = int(size / current_scale)
            if low_res < 2: low_res = 2
            noise_layer = np.random.randint(0, 255, (low_res, low_res), dtype=np.uint8)
            img = Image.fromarray(noise_layer)
            img = img.resize((size, size), resample=Image.BICUBIC)
            if i == 0:
                img = img.filter(ImageFilter.GaussianBlur(radius=size/150))
            
            layer_data = np.array(img, dtype=np.float32) / 255.0
            
            final_map += layer_data * amplitude
            max_value += amplitude
            
            amplitude *= 0.5
            frequency *= 2.0
        
        return final_map / max_value

    def generate_normal_from_height(self, height_map, intensity):
        """Generates a normal map from height data."""
        self.update_status("Calculating Normal Map...")
        gy, gx = np.gradient(height_map)
        
        gx *= intensity
        gy *= intensity
        
        norm = np.sqrt(gx**2 + gy**2 + 1.0)
        nx = ((gx / norm) + 1.0) / 2.0 * 255.0
        ny = ((gy / norm) + 1.0) / 2.0 * 255.0
        nz = (1.0 / norm) * 255.0
        
        normal_map = np.dstack((nx, ny, nz)).astype(np.uint8)
        return Image.fromarray(normal_map)

    def process_textures(self, t_type, size, scale, octaves, density, color_var, normal_str):
        
        res_mult = size / 1024
        adj_scale = scale * (res_mult * 0.5) 
        if adj_scale < 10: adj_scale = 10
        
        height_map = self.generate_layered_noise(size, adj_scale, octaves)
        
        self.update_status("Coloring & Compositing...")
        
        albedo = np.zeros((size, size, 3), dtype=np.uint8)
        roughness = np.zeros((size, size), dtype=np.uint8)

        if t_type == "Grass":
            img_h = Image.fromarray((height_map * 255).astype(np.uint8))
            img_h = img_h.resize((size, size//8))
            img_h = img_h.resize((size, size), resample=Image.BICUBIC)
            h_strands = np.array(img_h) / 255.0
            
            fresh_green = np.array([30, 140, 20])
            dark_green = np.array([10, 40, 5])
            dead_yellow = np.array([160, 140, 60])
            
            for i in range(3):
                base = dark_green[i] * (1 - h_strands) + fresh_green[i] * h_strands
                dead_mask = np.where(height_map < (1.0 - color_var), 0, 1)
                albedo[:,:,i] = np.where(dead_mask, base, dead_yellow[i]*0.7 + base*0.3)
            
            roughness = (h_strands * 0.6 + 0.3) * 255
            
            n_source = h_strands

        else:
            wet_mud = np.array([45, 35, 25])
            dry_dirt = np.array([110, 95, 75])
            rock_grey = np.array([100, 100, 100])
            
            for i in range(3):
                albedo[:,:,i] = wet_mud[i] * (1 - height_map) + dry_dirt[i] * height_map
                
            pebble_noise = np.random.rand(size, size)
            pebble_mask = pebble_noise > (1.0 - density * 0.2)
            
            for i in range(3):
                albedo[:,:,i] = np.where(pebble_mask, rock_grey[i] + (pebble_noise*40), albedo[:,:,i])
                
            roughness = height_map * 255
            roughness = np.where(pebble_mask, 200, roughness)
            
            n_source = height_map + (np.where(pebble_mask, 0.1, 0))

        img_albedo = Image.fromarray(albedo.astype(np.uint8))
        img_roughness = Image.fromarray(roughness.astype(np.uint8))
        
        img_normal = self.generate_normal_from_height(n_source, normal_str)
        
        return img_albedo, img_normal, img_roughness


    def start_generation(self):
        if self.is_generating: return
        
        self.is_generating = True
        self.btn_gen.config(state="disabled", text="GENERATING...")
        self.btn_save.config(state="disabled")
        self.progress_bar.start(10)
        
        threading.Thread(target=self.run_generation_thread, daemon=True).start()

    def update_status(self, text):
        self.root.after(0, lambda: self.status_label.config(text=text))

    def run_generation_thread(self):
        try:
            params = {
                "t_type": self.type_var.get(),
                "size": self.res_var.get(),
                "scale": self.scale_var.get(),
                "octaves": self.octaves_var.get(),
                "density": self.density_var.get(),
                "color_var": self.color_var.get(),
                "normal_str": self.normal_str_var.get()
            }
            
            start_time = time.time()
            
            alb, nrm, rgh = self.process_textures(**params)
            
            self.generated_maps = {"Albedo": alb, "Normal": nrm, "Roughness": rgh}
            
            elapsed = round(time.time() - start_time, 2)
            self.update_status(f"Done! Generation took {elapsed}s")
            
            self.root.after(0, self.finish_generation)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Memory or Calculation Error:\n{str(e)}"))
            self.root.after(0, self.reset_ui)

    def finish_generation(self):
        if "Albedo" in self.generated_maps:
            preview = self.generated_maps["Albedo"].resize((600, 600))
            self.preview_image = ImageTk.PhotoImage(preview)
            self.canvas.delete("all")
            self.canvas.create_image(300, 300, image=self.preview_image)
        
        self.reset_ui()

    def reset_ui(self):
        self.is_generating = False
        self.btn_gen.config(state="normal", text="GENERATE TEXTURE")
        self.btn_save.config(state="normal")
        self.progress_bar.stop()
        self.progress_var.set(100)

    def save_textures(self):
        if not self.generated_maps:
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if not file_path:
            return
            
        base_name = file_path.replace(".png", "")
        
        self.update_status("Saving files... (This may take a moment for 8K/16K)")
        self.root.update()
        
        try:
            self.generated_maps["Albedo"].save(f"{base_name}_Albedo.png")
            self.generated_maps["Normal"].save(f"{base_name}_Normal.png")
            self.generated_maps["Roughness"].save(f"{base_name}_Roughness.png")
            messagebox.showinfo("Success", "Textures exported successfully!")
            self.status_label.config(text="Saved.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = TextureGeneratorApp(root)
    root.mainloop()