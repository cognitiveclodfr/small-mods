#!/usr/bin/env python3
"""
Warehouse Label Generator v3.9 - DYNAMIC BARCODES FOR MOBILE SCANNERS
- Dynamic SKU font size (12-24pt) adapts to label width
- Optimized barcode width for long SKUs (0.75-1.2 barWidth)
- Enhanced readability for 203 DPI thermal printers
- Mobile scanner compatibility with minimum 0.75 X-dimension
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from datetime import datetime
import os
import pandas as pd

def setup_fonts():
    """Setup fonts for Cyrillic support"""
    try:
        font_paths = {
            'regular': [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/System/Library/Fonts/Supplemental/Arial.ttf',
                'C:\\Windows\\Fonts\\arial.ttf',
            ],
            'bold': [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                'C:\\Windows\\Fonts\\arialbd.ttf',
            ]
        }
        
        fonts_registered = {'regular': False, 'bold': False}
        
        for font_path in font_paths['regular']:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('Custom', font_path))
                    fonts_registered['regular'] = True
                    break
                except:
                    continue
        
        for font_path in font_paths['bold']:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('CustomBold', font_path))
                    fonts_registered['bold'] = True
                    break
                except:
                    continue
        
        return fonts_registered['regular'] and fonts_registered['bold']
    except:
        return False

class LabelGeneratorV3:
    def __init__(self, root):
        self.root = root
        self.root.title("Warehouse Label Generator v3.9")
        self.root.geometry("600x620")
        
        self.cyrillic_support = setup_fonts()
        
        self.master_data = {}
        self.current_file = None
        
        script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
        self.save_folder = script_dir
        
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        title = ttk.Label(main_frame, text="📦 Warehouse Label Generator v3.9", 
                         font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Database section
        db_frame = ttk.LabelFrame(main_frame, text="Master Database", padding="10")
        db_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        
        self.db_status = ttk.Label(db_frame, text="No database loaded", 
                                   foreground="red", font=('Arial', 9))
        self.db_status.grid(row=0, column=0, sticky=tk.W)
        
        load_btn = ttk.Button(db_frame, text="Load Excel/CSV", 
                             command=self.load_database)
        load_btn.grid(row=0, column=1, padx=10)
        
        # Positions mode checkbox
        self.positions_mode = tk.BooleanVar(value=False)
        self.last_loaded_file = None
        positions_check = ttk.Checkbutton(db_frame, text="Include warehouse positions (Поз. column)", 
                                         variable=self.positions_mode,
                                         command=self.on_positions_mode_change)
        positions_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(db_frame, text="⚠️ Auto-reloads CSV when changed", 
                 foreground="orange", font=('Arial', 8)).grid(
            row=2, column=0, columnspan=2, sticky=tk.W)
        
        # Generation mode
        mode_frame = ttk.LabelFrame(main_frame, text="Generation Mode", padding="10")
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.gen_mode = tk.StringVar(value="label_only")
        
        ttk.Radiobutton(mode_frame, text="Label Only (main label)", 
                       variable=self.gen_mode, value="label_only").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="Label + Attachment (label + positions page)", 
                       variable=self.gen_mode, value="both").grid(row=1, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="Attachment Only (positions page only)", 
                       variable=self.gen_mode, value="attachment_only").grid(row=2, column=0, sticky=tk.W)
        
        # Custom header
        header_frame = ttk.LabelFrame(main_frame, text="Label Header", padding="10")
        header_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(header_frame, text="Header text:", font=('Arial', 9)).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.header_var = tk.StringVar(value="WAREHOUSE STORAGE")
        header_entry = ttk.Entry(header_frame, textvariable=self.header_var, 
                                width=40, font=('Arial', 10))
        header_entry.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Frame(main_frame, height=2, relief='sunken').grid(
            row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # SKU selection
        ttk.Label(main_frame, text="SKU:", font=('Arial', 10, 'bold')).grid(
            row=5, column=0, sticky=tk.W, pady=5)
        
        self.sku_var = tk.StringVar()
        self.sku_combo = ttk.Combobox(main_frame, textvariable=self.sku_var, 
                                     width=30, font=('Arial', 10), state='disabled')
        self.sku_combo.grid(row=5, column=1, columnspan=2, sticky=tk.W, pady=5)
        self.sku_combo.bind('<<ComboboxSelected>>', self.on_sku_select)
        self.sku_combo.bind('<KeyRelease>', self.filter_sku)
        
        # Product name (auto-filled)
        ttk.Label(main_frame, text="Product Name:", font=('Arial', 10)).grid(
            row=6, column=0, sticky=tk.W, pady=5)
        
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, 
                              width=40, font=('Arial', 10), state='readonly')
        name_entry.grid(row=6, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Client (auto-filled)
        ttk.Label(main_frame, text="Client:", font=('Arial', 10)).grid(
            row=7, column=0, sticky=tk.W, pady=5)
        
        self.client_var = tk.StringVar()
        client_entry = ttk.Entry(main_frame, textvariable=self.client_var, 
                                width=40, font=('Arial', 10), state='readonly')
        client_entry.grid(row=7, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Quantity (optional)
        ttk.Label(main_frame, text="Quantity (optional):", font=('Arial', 10)).grid(
            row=8, column=0, sticky=tk.W, pady=5)
        
        self.qty_entry = ttk.Entry(main_frame, width=15, font=('Arial', 10))
        self.qty_entry.grid(row=8, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="Leave empty if not needed", 
                 foreground="gray", font=('Arial', 8)).grid(
            row=8, column=2, sticky=tk.W, padx=(5, 0))
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=9, column=0, columnspan=3, pady=15)
        
        self.gen_btn = ttk.Button(btn_frame, text="Generate PDF (Ctrl+G)", 
                                 command=self.generate_label, state='disabled')
        self.gen_btn.grid(row=0, column=0, padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="Clear (Ctrl+R)", 
                              command=self.clear_fields)
        clear_btn.grid(row=0, column=1, padx=5)
        
        # Status bar
        self.status = ttk.Label(main_frame, text=f"Save: {self.save_folder}", 
                               relief='sunken', font=('Arial', 8))
        self.status.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        # Keyboard shortcuts
        root.bind('<Control-g>', lambda e: self.generate_label())
        root.bind('<Control-r>', lambda e: self.clear_fields())
        root.bind('<Control-l>', lambda e: self.load_database())
        root.bind('<Return>', self.on_enter)
    
    def on_positions_mode_change(self):
        """Handle positions mode checkbox change - auto reload"""
        if self.last_loaded_file and os.path.exists(self.last_loaded_file):
            mode = "with positions" if self.positions_mode.get() else "without positions"
            print(f"\n=== Checkbox changed: {mode} ===")
            print(f"Auto-reloading: {os.path.basename(self.last_loaded_file)}")
            
            self.master_data = {}
            self.clear_fields()
            self._load_file_internal(self.last_loaded_file)
        else:
            mode = "enabled" if self.positions_mode.get() else "disabled"
            print(f"\n=== Positions mode {mode} (no file loaded yet) ===")
    
    def load_database(self):
        """Load Excel/CSV with positions support"""
        filepath = filedialog.askopenfilename(
            title="Select Master Database",
            filetypes=[
                ("Excel/CSV files", "*.xlsx *.xls *.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if not filepath:
            return
        
        self.last_loaded_file = filepath
        self._load_file_internal(filepath)
    
    def _load_file_internal(self, filepath):
        """Internal method to load file with current settings"""
        try:
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath, encoding='utf-8-sig')
            else:
                df = pd.read_excel(filepath)
            
            print(f"\n=== Loading {os.path.basename(filepath)} ===")
            print(f"Positions mode: {self.positions_mode.get()}")
            
            column_mapping = {
                'Фирма': 'client',
                'Артикул': 'sku',
                'Име': 'name',
                'Поз.': 'position',
                'Поз': 'position',
                'Client': 'client',
                'SKU': 'sku',
                'Name': 'name',
                'Product': 'name',
                'Company': 'client',
                'Position': 'position'
            }
            
            df_renamed = df.rename(columns=column_mapping)
            
            if not all(col in df_renamed.columns for col in ['sku', 'name', 'client']):
                if len(df.columns) >= 3:
                    df_renamed = df.iloc[:, :3].copy()
                    df_renamed.columns = ['client', 'sku', 'name']
                else:
                    raise ValueError("Could not find required columns")
            
            df_clean = df_renamed.dropna(subset=['sku'])
            df_clean = df_clean[df_clean['sku'].astype(str).str.strip() != '']
            df_clean = df_clean[~df_clean['sku'].astype(str).str.lower().str.contains('общо|total|sum', na=False)]
            
            self.master_data = {}
            positions_mode = self.positions_mode.get()
            
            for _, row in df_clean.iterrows():
                sku_raw = row['sku']
                if pd.notna(sku_raw):
                    try:
                        sku_float = float(sku_raw)
                        if sku_float == int(sku_float):
                            sku = str(int(sku_float)).strip()
                        else:
                            sku = str(sku_float).strip()
                    except (ValueError, TypeError):
                        sku = str(sku_raw).strip()
                else:
                    sku = ''
                
                name = str(row['name']).strip()
                client = str(row['client']).strip()
                
                position = ''
                if positions_mode and 'position' in df_renamed.columns:
                    pos_raw = row.get('position', '')
                    if pd.notna(pos_raw):
                        position = str(pos_raw).strip()
                
                if sku and name and client:
                    if positions_mode:
                        if sku not in self.master_data:
                            self.master_data[sku] = {
                                'name': name,
                                'client': client,
                                'positions': []
                            }
                        if position and position not in self.master_data[sku]['positions']:
                            self.master_data[sku]['positions'].append(position)
                            print(f"  SKU {sku}: position {position}")
                    else:
                        self.master_data[sku] = {
                            'name': name,
                            'client': client,
                            'positions': []
                        }
            
            if not self.master_data:
                raise ValueError("No valid data found in file")
            
            self.current_file = os.path.basename(filepath)
            mode_text = "with positions" if positions_mode else "without positions"
            self.db_status.config(
                text=f"✓ Loaded: {self.current_file} ({len(self.master_data)} products, {mode_text})",
                foreground="green"
            )
            
            self.sku_combo['state'] = 'normal'
            self.sku_combo['values'] = sorted(self.master_data.keys())
            self.sku_combo.focus()
            
            messagebox.showinfo("Success", f"Loaded {len(self.master_data)} products {mode_text}!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load database:\n{str(e)}")
            self.db_status.config(text="✗ Failed to load database", foreground="red")
    
    def filter_sku(self, event=None):
        """Filter SKU list as user types"""
        if not self.master_data:
            return
        
        typed = self.sku_var.get().lower()
        if typed == '':
            self.sku_combo['values'] = sorted(self.master_data.keys())
        else:
            filtered = [sku for sku in self.master_data.keys() if typed in sku.lower()]
            self.sku_combo['values'] = sorted(filtered)
    
    def on_sku_select(self, event=None):
        """Auto-fill when SKU is selected"""
        sku = self.sku_var.get()
        if sku in self.master_data:
            self.name_var.set(self.master_data[sku]['name'])
            self.client_var.set(self.master_data[sku]['client'])
            
            positions = self.master_data[sku].get('positions', [])
            if positions:
                print(f"SKU {sku} has {len(positions)} positions: {positions}")
            
            self.qty_entry.focus()
            self.gen_btn['state'] = 'normal'
    
    def on_enter(self, event=None):
        """Handle Enter key"""
        if self.gen_btn['state'] == 'normal':
            self.generate_label()
        else:
            if self.sku_var.get():
                self.on_sku_select()
    
    def clear_fields(self):
        """Clear selection"""
        self.sku_var.set('')
        self.name_var.set('')
        self.client_var.set('')
        self.qty_entry.delete(0, tk.END)
        self.sku_combo.focus()
        if self.master_data:
            self.sku_combo['values'] = sorted(self.master_data.keys())
    
    def generate_label(self):
        """Generate PDF with selected mode"""
        if not self.master_data:
            messagebox.showwarning("No Database", "Please load database first!")
            return
        
        sku = self.sku_var.get()
        qty = self.qty_entry.get().strip()
        
        if not sku or sku not in self.master_data:
            messagebox.showwarning("Invalid SKU", "Please select a valid SKU!")
            return
        
        if qty and not qty.isdigit():
            messagebox.showwarning("Invalid Quantity", "Quantity must be a number or empty!")
            return
        
        data = {
            'sku': sku,
            'name': self.name_var.get(),
            'client': self.client_var.get(),
            'quantity': qty if qty else None,
            'header': self.header_var.get(),
            'positions': self.master_data[sku].get('positions', [])
        }
        
        client_name = data['client']
        safe_client_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).strip()
        client_folder = os.path.join(self.save_folder, safe_client_name)
        
        try:
            os.makedirs(client_folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create folder:\n{str(e)}")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = self.gen_mode.get()
        
        try:
            if mode == "label_only":
                filename = f"{sku}_{timestamp}.pdf"
                filepath = os.path.join(client_folder, filename)
                self.create_main_label(filepath, data)
                msg = f"✓ Label generated: {filename}"
                
            elif mode == "both":
                filename = f"{sku}_{timestamp}.pdf"
                filepath = os.path.join(client_folder, filename)
                self.create_label_with_attachment(filepath, data)
                msg = f"✓ Label + Attachment generated: {filename}"
                
            elif mode == "attachment_only":
                filename = f"{sku}_attachment_{timestamp}.pdf"
                filepath = os.path.join(client_folder, filename)
                self.create_attachment_only(filepath, data)
                msg = f"✓ Attachment generated: {filename}"
            
            self.status.config(text=msg, foreground="green")
            messagebox.showinfo("Success", msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate:\n{str(e)}")
            self.status.config(text="✗ Error", foreground="red")
    
    def calculate_optimal_barwidth(self, sku_value, available_width_mm, target_height_mm=30, 
                                   max_width=1.2, min_width=0.75):
        """
        Розраховує оптимальний barWidth для баркоду щоб вміщався і був читабельний.
        
        Для 203 dpi принтера:
        - min_width=0.75 (~0.264mm X-dimension) - мінімум для надійного сканування
        - max_width=1.2 (~0.42mm X-dimension) - оптимум для коротких кодів
        """
        # Тестуємо різні barWidth від максимального до мінімального
        for bar_width in [w/10 for w in range(int(max_width*10), int(min_width*10)-1, -1)]:
            try:
                test_barcode = code128.Code128(str(sku_value), 
                                               barHeight=target_height_mm*mm, 
                                               barWidth=bar_width)
                barcode_width_mm = test_barcode.width / mm
                
                # Якщо баркод вміщується з запасом 2mm
                if barcode_width_mm <= (available_width_mm - 2):
                    return bar_width
            except:
                continue
        
        # Якщо не вміщається навіть з мінімальним - повертаємо мінімум (краще читабельність)
        return min_width
    
    def create_main_label(self, filepath, data):
        """Create main label page (100x150mm)"""
        width = 100 * mm
        height = 150 * mm
        
        c = canvas.Canvas(filepath, pagesize=(width, height))
        
        if self.cyrillic_support:
            font_regular = "Custom"
            font_bold = "CustomBold"
        else:
            font_regular = "Helvetica"
            font_bold = "Helvetica-Bold"
        
        border_padding = 3*mm
        c.setLineWidth(0.5)
        c.rect(border_padding, border_padding, 
               width - 2*border_padding, height - 2*border_padding, 
               stroke=1, fill=0)
        
        left_margin = 8*mm
        right_margin = width - 8*mm
        y_position = height - 15*mm
        
        # Header
        c.setFont(font_bold, 14)
        c.drawString(left_margin, y_position, data['header'])
        
        y_position -= 12*mm
        c.line(left_margin, y_position, right_margin, y_position)
        
        # SKU - динамічний розмір шрифту (12-24pt)
        y_position -= 18*mm
        sku_text = f"SKU: {data['sku']}"
        available_width = right_margin - left_margin
        optimal_size = 24
        
        for size in range(24, 11, -1):
            text_width = c.stringWidth(sku_text, font_bold, size)
            if text_width <= available_width:
                optimal_size = size
                break
        
        c.setFont(font_bold, optimal_size)
        c.drawString(left_margin, y_position, sku_text)
        
        # Product
        y_position -= 16*mm
        c.setFont(font_bold, 16)
        c.drawString(left_margin, y_position, "Product:")
        
        c.setFont(font_regular, 13)
        name = data['name']
        chars_per_line = 35
        
        if len(name) <= chars_per_line:
            c.drawString(left_margin, y_position - 5*mm, name)
            y_position -= 13*mm
        else:
            words = name.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if len(test_line) <= chars_per_line:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            lines = lines[:2]
            if len(data['name']) > chars_per_line * 2:
                lines[-1] = lines[-1][:chars_per_line-3] + "..."
            
            for i, line in enumerate(lines):
                c.drawString(left_margin, y_position - (5 + i*4)*mm, line)
            
            y_position -= (13 + (len(lines)-1)*4)*mm
        
        # Client
        y_position -= 15*mm
        c.setFont(font_bold, 16)
        c.drawString(left_margin, y_position, "Client:")
        c.setFont(font_regular, 13)
        client = data['client'][:chars_per_line]
        c.drawString(left_margin, y_position - 5*mm, client)
        
        # Quantity
        qty_bottom_y = None
        if data.get('quantity'):
            y_position -= 18*mm
            c.setFont(font_bold, 20)
            c.drawString(left_margin, y_position, f"QTY: {data['quantity']} pcs")
            c.setLineWidth(1)
            c.rect(left_margin - 2*mm, y_position - 3*mm, 
                   75*mm, 12*mm, stroke=1, fill=0)
            qty_bottom_y = y_position - 3*mm
        
        # Calculate maximum barcode space
        # Top limit: bottom of QTY box or last content
        if qty_bottom_y:
            barcode_top_limit = qty_bottom_y - 5*mm
        else:
            barcode_top_limit = y_position - 10*mm
        
        # Bottom limit: timestamp area (need 5mm for timestamp at 8mm from bottom)
        timestamp_y = 8*mm
        barcode_bottom_limit = timestamp_y + 3*mm  # 3mm above timestamp
        
        # Available space for barcode
        available_height = barcode_top_limit - barcode_bottom_limit
        
        # Use maximum height for barcode (leave some padding)
        barcode_height = available_height - 2*mm
        
        # SKU Barcode (MAXIMUM height) з оптимізованою шириною
        try:
            # Розраховуємо оптимальний barWidth для довгих SKU
            available_width_mm = (right_margin - left_margin) / mm
            optimal_barwidth = self.calculate_optimal_barwidth(
                data['sku'], 
                available_width_mm, 
                target_height_mm=barcode_height/mm
            )
            
            barcode = code128.Code128(str(data['sku']), 
                                     barHeight=barcode_height, 
                                     barWidth=optimal_barwidth)
            barcode_x = (width - barcode.width) / 2
            barcode_y = barcode_bottom_limit
            barcode.drawOn(c, barcode_x, barcode_y)
            print(f"Main label: SKU barcode {barcode.width/mm:.1f}mm x {barcode_height/mm:.1f}mm (barWidth={optimal_barwidth})")
        except Exception as e:
            print(f"Barcode failed: {e}")
        
        # Date (at fixed position)
        c.setFont(font_regular, 8)
        c.drawString(left_margin, timestamp_y, 
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        c.save()
    
    def draw_position_sector(self, c, position, sector_x, sector_y, sector_width, sector_height, warehouse_code="C100"):
        """Draw position sector with STANDARDIZED text placement"""
        if self.cyrillic_support:
            font_bold = "CustomBold"
        else:
            font_bold = "Helvetica-Bold"
        
        # Draw sector border
        c.setLineWidth(0.5)
        c.rect(sector_x, sector_y, sector_width, sector_height, stroke=1, fill=0)
        
        # STANDARDIZED text placement - always 3mm from left, 6mm from top
        text_padding_left = 3*mm
        text_padding_top = 6*mm
        text_x = sector_x + text_padding_left
        text_y = sector_y + sector_height - text_padding_top
        
        c.setFont(font_bold, 14)
        c.drawString(text_x, text_y, position)
        
        # Barcode - FIXED 15mm height, оптимізована ширина
        barcode_padding_sides = 4*mm
        barcode_padding_bottom = 4*mm
        
        try:
            barcode_value = warehouse_code + position
            sector_available_width = (sector_width - 2*barcode_padding_sides) / mm
            
            # Оптимізуємо barWidth (0.75-0.9 для позицій)
            optimal_barwidth = self.calculate_optimal_barwidth(
                barcode_value, 
                sector_available_width, 
                target_height_mm=15,
                max_width=0.9,
                min_width=0.75
            )
            
            pos_barcode = code128.Code128(barcode_value, 
                                         barHeight=15*mm,
                                         barWidth=optimal_barwidth)
            
            barcode_x = sector_x + (sector_width - pos_barcode.width) / 2
            barcode_y = sector_y + barcode_padding_bottom
            
            pos_barcode.drawOn(c, barcode_x, barcode_y)
            print(f"  ✓ {position} -> {barcode_value} [barWidth={optimal_barwidth}]")
        except Exception as e:
            print(f"  ✗ Barcode failed for {position}: {e}")
    
    def create_positions_grid_1x2(self, c, positions, y_start, left_margin, right_margin):
        """Draw 1x2 grid with standardized layout"""
        warehouse_code = "C100"
        
        grid_width = right_margin - left_margin
        grid_height = 58*mm
        
        sector_width = grid_width
        sector_height = grid_height / 2
        
        print(f"\n1x2 Grid: {sector_width/mm:.1f}mm x {sector_height/mm:.1f}mm per sector")
        
        for i, position in enumerate(positions[:2]):
            row = i
            
            sector_x = left_margin
            sector_y = y_start - ((row + 1) * sector_height)
            
            self.draw_position_sector(c, position, sector_x, sector_y, 
                                     sector_width, sector_height, warehouse_code)
        
        return y_start - grid_height
    
    def create_positions_grid_1x3(self, c, positions, y_start, left_margin, right_margin, start_idx):
        """Draw 1x3 grid with standardized layout - smaller barcodes to fit"""
        warehouse_code = "C100"
        
        if self.cyrillic_support:
            font_bold = "CustomBold"
        else:
            font_bold = "Helvetica-Bold"
        
        grid_width = right_margin - left_margin
        grid_height = 58*mm
        
        sector_width = grid_width
        sector_height = grid_height / 3  # ~29.0mm
        
        print(f"\n1x3 Grid (positions {start_idx+1}-{start_idx+len(positions)}): {sector_width/mm:.1f}mm x {sector_height/mm:.1f}mm per sector")
        
        for i, position in enumerate(positions[:3]):
            row = i
            
            sector_x = left_margin
            sector_y = y_start - ((row + 1) * sector_height)
            
            # Draw sector border
            c.setLineWidth(0.5)
            c.rect(sector_x, sector_y, sector_width, sector_height, stroke=1, fill=0)
            
            # STANDARDIZED text placement - same as 1x2
            text_padding_left = 3*mm
            text_padding_top = 6*mm
            text_x = sector_x + text_padding_left
            text_y = sector_y + sector_height - text_padding_top
            
            c.setFont(font_bold, 14)
            c.drawString(text_x, text_y, position)
            
            # SMALLER barcode (10mm) to fit in small sector, оптимізована ширина
            barcode_padding_bottom = 3*mm
            barcode_padding_sides = 3*mm
            
            try:
                barcode_value = warehouse_code + position
                sector_available_width = (sector_width - 2*barcode_padding_sides) / mm
                
                # Оптимізуємо barWidth (0.75-0.9 для позицій)
                optimal_barwidth = self.calculate_optimal_barwidth(
                    barcode_value, 
                    sector_available_width, 
                    target_height_mm=10,
                    max_width=0.9,
                    min_width=0.75
                )
                
                pos_barcode = code128.Code128(barcode_value, 
                                             barHeight=10*mm,  # Smaller for 1x3!
                                             barWidth=optimal_barwidth)
                
                barcode_x = sector_x + (sector_width - pos_barcode.width) / 2
                barcode_y = sector_y + barcode_padding_bottom
                
                pos_barcode.drawOn(c, barcode_x, barcode_y)
                print(f"  ✓ {position} -> {barcode_value} [10mm, barWidth={optimal_barwidth}]")
            except Exception as e:
                print(f"  ✗ Barcode failed for {position}: {e}")
        
        return y_start - grid_height
    
    def create_attachment_page(self, c, data):
        """Create attachment page with 1x2 grid for first 2 positions"""
        width = 100 * mm
        height = 150 * mm
        
        if self.cyrillic_support:
            font_regular = "Custom"
            font_bold = "CustomBold"
        else:
            font_regular = "Helvetica"
            font_bold = "Helvetica-Bold"
        
        border_padding = 3*mm
        c.setLineWidth(0.5)
        c.rect(border_padding, border_padding, 
               width - 2*border_padding, height - 2*border_padding, 
               stroke=1, fill=0)
        
        left_margin = 8*mm
        right_margin = width - 8*mm
        y_position = height - 10*mm
        
        # Client
        c.setFont(font_bold, 14)
        client_text = data['client']
        
        if len(client_text) > 30:
            words = client_text.split()
            line1 = ""
            line2 = ""
            for word in words:
                if len(line1) < 30 and not line2:
                    line1 = line1 + " " + word if line1 else word
                else:
                    line2 = line2 + " " + word if line2 else word
            
            c.drawString(left_margin, y_position, line1)
            y_position -= 5*mm
            c.drawString(left_margin, y_position, line2[:30])
            y_position -= 8*mm
        else:
            c.drawString(left_margin, y_position, client_text)
            y_position -= 10*mm
        
        c.line(left_margin, y_position, right_margin, y_position)
        
        # SKU - динамічний розмір (10-14pt)
        y_position -= 10*mm
        sku_text = f"SKU: {data['sku']}"
        available_width = right_margin - left_margin
        optimal_size = 14
        
        for size in range(14, 9, -1):
            text_width = c.stringWidth(sku_text, font_bold, size)
            if text_width <= available_width:
                optimal_size = size
                break
        
        c.setFont(font_bold, optimal_size)
        c.drawString(left_margin, y_position, sku_text)
        
        # SKU Barcode з оптимізованою шириною
        y_position -= 3*mm
        try:
            available_width_mm = (right_margin - left_margin) / mm
            optimal_barwidth = self.calculate_optimal_barwidth(
                data['sku'], 
                available_width_mm, 
                target_height_mm=12
            )
            
            sku_barcode = code128.Code128(str(data['sku']), 
                                         barHeight=12*mm, 
                                         barWidth=optimal_barwidth)
            barcode_x = (width - sku_barcode.width) / 2
            sku_barcode.drawOn(c, barcode_x, y_position - 12*mm)
            y_position -= 15*mm
            print(f"Attachment: SKU barcode {sku_barcode.width/mm:.1f}mm (barWidth={optimal_barwidth})")
        except Exception as e:
            print(f"SKU barcode failed: {e}")
            y_position -= 12*mm
        
        c.line(left_margin, y_position, right_margin, y_position)
        
        # Positions
        positions = data.get('positions', [])
        
        if positions:
            y_position -= 8*mm
            c.setFont(font_bold, 11)
            pos_text = f"Warehouse Positions (1-{min(2, len(positions))} of {len(positions)}):" if len(positions) > 2 else "Warehouse Positions:"
            c.drawString(left_margin, y_position, pos_text)
            
            y_position -= 4*mm
            
            # 1x2 grid for first 2 positions
            y_position = self.create_positions_grid_1x2(c, positions, y_position, left_margin, right_margin)
            
            if len(positions) > 2:
                y_position -= 6*mm
                c.setFont(font_regular, 9)
                c.drawString(left_margin, y_position, 
                           f"→ Continued on next page ({len(positions) - 2} more positions)")
        else:
            y_position -= 10*mm
            c.setFont(font_regular, 11)
            c.drawString(left_margin, y_position, "No positions assigned")
        
        # Date
        c.setFont(font_regular, 8)
        c.drawString(left_margin, border_padding + 5*mm, 
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    def create_continuation_page(self, c, data, start_idx):
        """Create continuation page with 1x3 grid for positions 3+"""
        width = 100 * mm
        height = 150 * mm
        
        if self.cyrillic_support:
            font_regular = "Custom"
            font_bold = "CustomBold"
        else:
            font_regular = "Helvetica"
            font_bold = "Helvetica-Bold"
        
        border_padding = 3*mm
        c.setLineWidth(0.5)
        c.rect(border_padding, border_padding, 
               width - 2*border_padding, height - 2*border_padding, 
               stroke=1, fill=0)
        
        left_margin = 8*mm
        right_margin = width - 8*mm
        y_position = height - 10*mm
        
        # Header
        c.setFont(font_bold, 14)
        c.drawString(left_margin, y_position, data['client'][:40])
        
        y_position -= 8*mm
        
        # SKU - динамічний розмір (8-12pt для компактності)
        sku_text = f"SKU: {data['sku']}"
        available_width = right_margin - left_margin
        optimal_size = 12
        
        for size in range(12, 7, -1):
            text_width = c.stringWidth(sku_text, font_bold, size)
            if text_width <= available_width:
                optimal_size = size
                break
        
        c.setFont(font_bold, optimal_size)
        c.drawString(left_margin, y_position, sku_text)
        
        y_position -= 10*mm
        c.line(left_margin, y_position, right_margin, y_position)
        
        # Positions
        positions = data.get('positions', [])
        end_idx = min(start_idx + 3, len(positions))
        
        y_position -= 8*mm
        c.setFont(font_bold, 11)
        c.drawString(left_margin, y_position, 
                    f"Warehouse Positions ({start_idx + 1}-{end_idx} of {len(positions)}):")
        
        y_position -= 4*mm
        
        # 1x3 grid with STANDARDIZED text placement
        positions_slice = positions[start_idx:end_idx]
        y_position = self.create_positions_grid_1x3(c, positions_slice, y_position, left_margin, right_margin, start_idx)
        
        if end_idx < len(positions):
            y_position -= 6*mm
            c.setFont(font_regular, 9)
            c.drawString(left_margin, y_position, 
                       f"→ Continued on next page ({len(positions) - end_idx} more positions)")
        
        # Date
        c.setFont(font_regular, 8)
        c.drawString(left_margin, border_padding + 5*mm, 
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    def create_label_with_attachment(self, filepath, data):
        """Create PDF with label and paginated position pages"""
        width = 100 * mm
        height = 150 * mm
        
        c = canvas.Canvas(filepath, pagesize=(width, height))
        
        # Page 1: Main label
        self.create_main_label_on_canvas(c, data)
        
        # Page 2: Attachment (first 2 positions in 1x2)
        c.showPage()
        self.create_attachment_page(c, data)
        
        # Additional pages for positions 3+ (3 per page in 1x3)
        positions = data.get('positions', [])
        if len(positions) > 2:
            start_idx = 2
            while start_idx < len(positions):
                c.showPage()
                self.create_continuation_page(c, data, start_idx)
                start_idx += 3
        
        c.save()
    
    def create_main_label_on_canvas(self, c, data):
        """Create main label on existing canvas"""
        width = 100 * mm
        height = 150 * mm
        
        if self.cyrillic_support:
            font_regular = "Custom"
            font_bold = "CustomBold"
        else:
            font_regular = "Helvetica"
            font_bold = "Helvetica-Bold"
        
        border_padding = 3*mm
        c.setLineWidth(0.5)
        c.rect(border_padding, border_padding, 
               width - 2*border_padding, height - 2*border_padding, 
               stroke=1, fill=0)
        
        left_margin = 8*mm
        right_margin = width - 8*mm
        y_position = height - 15*mm
        
        c.setFont(font_bold, 14)
        c.drawString(left_margin, y_position, data['header'])
        
        y_position -= 12*mm
        c.line(left_margin, y_position, right_margin, y_position)
        
        # SKU - динамічний розмір шрифту (12-24pt)
        y_position -= 18*mm
        sku_text = f"SKU: {data['sku']}"
        available_width = right_margin - left_margin
        optimal_size = 24
        
        for size in range(24, 11, -1):
            text_width = c.stringWidth(sku_text, font_bold, size)
            if text_width <= available_width:
                optimal_size = size
                break
        
        c.setFont(font_bold, optimal_size)
        c.drawString(left_margin, y_position, sku_text)
        
        y_position -= 16*mm
        c.setFont(font_bold, 16)
        c.drawString(left_margin, y_position, "Product:")
        
        c.setFont(font_regular, 13)
        name = data['name']
        chars_per_line = 35
        
        if len(name) <= chars_per_line:
            c.drawString(left_margin, y_position - 5*mm, name)
            y_position -= 13*mm
        else:
            words = name.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if len(test_line) <= chars_per_line:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            lines = lines[:2]
            if len(data['name']) > chars_per_line * 2:
                lines[-1] = lines[-1][:chars_per_line-3] + "..."
            
            for i, line in enumerate(lines):
                c.drawString(left_margin, y_position - (5 + i*4)*mm, line)
            
            y_position -= (13 + (len(lines)-1)*4)*mm
        
        y_position -= 15*mm
        c.setFont(font_bold, 16)
        c.drawString(left_margin, y_position, "Client:")
        c.setFont(font_regular, 13)
        client = data['client'][:chars_per_line]
        c.drawString(left_margin, y_position - 5*mm, client)
        
        qty_bottom_y = None
        if data.get('quantity'):
            y_position -= 18*mm
            c.setFont(font_bold, 20)
            c.drawString(left_margin, y_position, f"QTY: {data['quantity']} pcs")
            c.setLineWidth(1)
            c.rect(left_margin - 2*mm, y_position - 3*mm, 
                   75*mm, 12*mm, stroke=1, fill=0)
            qty_bottom_y = y_position - 3*mm
        
        # Calculate maximum barcode space
        if qty_bottom_y:
            barcode_top_limit = qty_bottom_y - 5*mm
        else:
            barcode_top_limit = y_position - 10*mm
        
        timestamp_y = 8*mm
        barcode_bottom_limit = timestamp_y + 3*mm
        
        available_height = barcode_top_limit - barcode_bottom_limit
        barcode_height = available_height - 2*mm
        
        # SKU Barcode (MAXIMUM) з оптимізованою шириною
        try:
            available_width_mm = (right_margin - left_margin) / mm
            optimal_barwidth = self.calculate_optimal_barwidth(
                data['sku'], 
                available_width_mm, 
                target_height_mm=barcode_height/mm
            )
            
            barcode = code128.Code128(str(data['sku']), 
                                     barHeight=barcode_height, 
                                     barWidth=optimal_barwidth)
            barcode_x = (width - barcode.width) / 2
            barcode_y = barcode_bottom_limit
            barcode.drawOn(c, barcode_x, barcode_y)
            print(f"Label on canvas: SKU barcode {barcode.width/mm:.1f}mm x {barcode_height/mm:.1f}mm (barWidth={optimal_barwidth})")
        except Exception as e:
            print(f"Barcode failed: {e}")
        
        c.setFont(font_regular, 8)
        c.drawString(left_margin, timestamp_y, 
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    def create_attachment_only(self, filepath, data):
        """Create attachment with pagination"""
        width = 100 * mm
        height = 150 * mm
        
        c = canvas.Canvas(filepath, pagesize=(width, height))
        
        # Page 1: First 2 positions (1x2)
        self.create_attachment_page(c, data)
        
        # Additional pages for positions 3+ (3 per page in 1x3)
        positions = data.get('positions', [])
        if len(positions) > 2:
            start_idx = 2
            while start_idx < len(positions):
                c.showPage()
                self.create_continuation_page(c, data, start_idx)
                start_idx += 3
        
        c.save()

def main():
    root = tk.Tk()
    app = LabelGeneratorV3(root)
    root.mainloop()

if __name__ == "__main__":
    main()
