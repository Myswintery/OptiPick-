import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import json
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from PIL import Image, ImageTk  # Pillow library

# Global Variables
product_data = []
user_budget = 0.0
last_recommendation = None

feature_weights = {
    "Cost Efficiency": 7,
    "Quality": 10,
    "Durability": 8,
    "User Experience": 6,
    "Support & Maintenance": 5,
    "Popularity / Trust": 6,
    "Long-Term Value": 7,
    "Customizability": 4
}

# Functions
def get_selected_features():
    return ", ".join([feat for feat, var in feature_vars.items() if var.get()])

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def add_product():
    name = entry_name.get().strip()
    price_text = entry_price.get().strip()
    features = get_selected_features()
    priority = entry_priority.get().strip()

    if not name or not price_text or not features:
        messagebox.showwarning("Input Error", "Please fill product name, price and select at least one feature.")
        return

    try:
        price = float(price_text)
    except ValueError:
        messagebox.showwarning("Input Error", "Price must be a valid number.")
        return

    product_data.append({
        'Name': name,
        'Price': price,
        'Features': features,
        'Score': 0,
        'Priority': priority if priority else "3"
    })

    entry_name.delete(0, tk.END)
    entry_price.delete(0, tk.END)
    entry_priority.delete(0, tk.END)
    for var in feature_vars.values():
        var.set(False)

    update_table()
    messagebox.showinfo("Success", "Product added successfully.")

def update_table():
    for r in table.get_children():
        table.delete(r)
    for item in product_data:
        table.insert("", "end", values=(item['Name'], item['Price'], item['Features'], item['Priority'], item['Score']))

def delete_selected():
    sel = table.selection()
    if not sel:
        messagebox.showwarning("Selection Error", "Please select a row to delete.")
        return

    if not messagebox.askyesno("Confirm Delete", "Delete selected product(s)?"):
        return

    for s in sel:
        vals = table.item(s, 'values')
        table.delete(s)
        # remove from product_data (first matching name+price)
        for i, item in enumerate(product_data):
            if item['Name'] == vals[0] and str(item['Price']) == str(vals[1]):
                del product_data[i]
                break

    update_table()

def recommend_product(go_to_stats=False):
    global last_recommendation, user_budget

    if not product_data:
        messagebox.showinfo("No Data", "Please add products first.")
        return

    try:
        budget = float(entry_budget.get())
        user_budget = budget
    except ValueError:
        messagebox.showwarning("Input Error", "Please enter a valid budget.")
        return

    best = None
    max_score = -float("inf")

    for item in product_data:
        score = 0
        price = item["Price"]
        features = [f.strip() for f in item['Features'].split(",") if f.strip()]

        # Price effect
        if user_budget == 0:
            # neutral, avoid division by zero: penalize heavily if price > 0 and budget is 0
            if price > 0:
                score -= 50
            else:
                score += 5
        else:
            if price > user_budget:
                over_percent = (price - user_budget) / user_budget
                score -= round(over_percent * 10)
            else:
                score += 5

        # Feature weights
        for f in features:
            score += feature_weights.get(f, 5)

        # Priority
        try:
            priority_level = int(item.get('Priority', 3))
        except Exception:
            priority_level = 3
        score += priority_level

        item['Score'] = score

        if score > max_score:
            max_score = score
            best = item

    update_table()

    if best:
        last_recommendation = best
        result_label.config(text=f"Best Recommendation:\n{best['Name']} (₹{best['Price']})\nFeatures: {best['Features']}\nScore: {best['Score']}", fg="#2E7D32")
    else:
        result_label.config(text="No suitable product found.", fg="#D32F2F")

    if go_to_stats:
        draw_statistics()
        notebook.select(frame_stats)

def export_recommendation_csv():
    if not product_data or not last_recommendation:
        messagebox.showwarning("Missing Data", "Please add products and get a recommendation first.")
        return

    path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if not path:
        return

    try:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Price", "Features", "Priority", "Score"])
            for p in product_data:
                writer.writerow([p['Name'], p['Price'], p['Features'], p['Priority'], p['Score']])
            writer.writerow([])
            writer.writerow([f"Recommended Product: {last_recommendation['Name']}"])
        messagebox.showinfo("Exported", f"Saved CSV to {path}")
    except Exception as e:
        messagebox.showerror("Export Error", str(e))

def save_product_list():
    if not product_data:
        messagebox.showwarning("No Data", "There are no products to save.")
        return

    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json")])
    if not path:
        return

    try:
        data = {"budget": user_budget, "products": product_data}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Saved", "Product list saved successfully.")
    except Exception as e:
        messagebox.showerror("Save Error", str(e))

def load_product_list():
    global product_data, user_budget, last_recommendation

    path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON files","*.json")])
    if not path:
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        product_data = loaded.get("products", [])
        user_budget = loaded.get("budget", 0.0)
        entry_budget.delete(0, tk.END)
        entry_budget.insert(0, str(user_budget))
        update_table()
        # run recommendation automatically after loading (but not auto-switch)
        recommend_product(go_to_stats=False)
        messagebox.showinfo("Loaded", "Product list loaded successfully.")
    except Exception as e:
        messagebox.showerror("Load Error", str(e))

def draw_statistics():
    # clear frame
    for widget in frame_stats.winfo_children():
        widget.destroy()

    if not product_data or not last_recommendation:
        tk.Label(frame_stats, text="No recommendation available. Add products and get recommendation first.",
                 font=("Helvetica", 14, "bold"), fg="#D32F2F", bg=frame_bg).grid(row=0, column=0, columnspan=2, pady=20)
        return

    if len(product_data) < 2:
        tk.Label(frame_stats, text="Not enough products to compare (need at least 2).",
                 font=("Helvetica", 14), fg="#D32F2F", bg=frame_bg).grid(row=0, column=0, columnspan=2, pady=20)
        return

    sns.set_style("whitegrid")

    # Product feature comparison (DataFrame)
    feature_names = sorted(feature_weights.keys())
    df_comp = []
    for p in product_data[:5]:  # first 5 products
        feats = [f.strip() for f in p['Features'].split(",") if f.strip()]
        for f in feature_names:
            score = feature_weights.get(f, 0) if f in feats else 0
            df_comp.append({"Product": p["Name"], "Feature": f, "Score": score})
    df_comp = pd.DataFrame(df_comp)

    # Grouped Bar Chart (features x products)
    fig1, ax1 = plt.subplots(figsize=(10, 4))
    sns.barplot(data=df_comp, x="Feature", y="Score", hue="Product", ax=ax1, palette="Set2")
    ax1.set_title("Products Feature Score Comparison")
    ax1.set_ylabel("Score")
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")
    fig1.tight_layout() # automatically adjust margins
    
    canvas1 = FigureCanvasTkAgg(fig1, master=frame_stats)
    canvas1.draw()
    canvas1.get_tk_widget().grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)

    # Budget vs Recommendation pie
    fig2, ax2 = plt.subplots(figsize=(3,3), subplot_kw={'aspect':'equal'})
    if user_budget == 0:
        percent_fit = 0.0
    else:
        percent_fit = min(last_recommendation["Price"] / user_budget, 1.5)
    used = min(percent_fit, 1.0)
    remaining = max(1.0 - used, 0.0)
    ax2.pie([used, remaining],
            labels=[f"Used ({used*100:.1f}%)", f"Remaining ({remaining*100:.1f}%)"],
            startangle=90, colors=['#4CAF50', '#E0E0E0'])
    ax2.set_title(f"Budget Fit (Based on ₹{user_budget:.2f})")
    
    canvas2 = FigureCanvasTkAgg(fig2, master=frame_stats)
    canvas2.draw()
    canvas2.get_tk_widget().grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

    # Confidence gauge
    fig3, ax3 = plt.subplots(figsize=(3,3))
    confidence = max(0.0, min(last_recommendation.get("Score", 0) / 100.0, 1.0))
    ax3.pie([confidence, 1-confidence], colors=['#0288D1', '#E0E0E0'], startangle=90)
    centre = plt.Circle((0,0), 0.7, fc='white')
    fig3.gca().add_artist(centre)
    ax3.set_title(f"Recommendation Confidence: {confidence*100:.1f}%")

    canvas3 = FigureCanvasTkAgg(fig3, master=frame_stats)
    canvas3.draw()
    canvas3.get_tk_widget().grid(row=2, column=1, sticky="nsew", padx=10, pady=10)

    # Table summary
    label_table = tk.Label(frame_stats, text="Top Products Overview",
                           font=("Helvetica", 14), bg=frame_bg, fg="black")
    label_table.grid(row=0, column=2, pady=5, padx=10)

    top_sorted = sorted(product_data, key=lambda x: x['Score'], reverse=True)[:5]
    cols = ("Name", "Price", "Score")
    tree = ttk.Treeview(frame_stats, columns=cols, show='headings', height=5)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=120)
    for p in top_sorted:
        tree.insert("", "end", values=(p['Name'], f"₹{p['Price']:.2f}", p['Score']))
    tree.grid(row=1, column=2, pady=10, padx=10, sticky="nsew")

# UI 
root = tk.Tk()
root.title("OptiPick - Optimal Product Recommender")
root.state('zoomed')
frame_bg = "#F5F5F5"
root.configure(bg=frame_bg)

# Favicon Conversion and Application
# logo_img = Image.open("AI_OptiPick_Logo.png")
# logo_img.save("favicon.ico", format="ICO", sizes=[(64,64)]) # Convert and save as ICO as 32x32 pixels
root.iconbitmap("favicon.ico")

# Style
style = ttk.Style()
style.theme_use('clam')
style.configure("TNotebook", background=frame_bg)
style.configure("TNotebook.Tab", font=("Helvetica", 12, "bold"), padding=[10,6])
style.map("TNotebook.Tab",
          background=[("selected", "#4CAF50"), ("!selected", "#E0E0E0")],
          foreground=[("selected","white"), ("!selected","#333333")])
style.configure("Treeview", font=("Helvetica", 10), rowheight=24)
style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"))

# Notebook and tabs
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=8, pady=8)

frame_add = tk.Frame(notebook, bg=frame_bg)
frame_table = tk.Frame(notebook, bg=frame_bg)
frame_stats = tk.Frame(notebook, bg=frame_bg)

notebook.add(frame_add, text="Home")
notebook.add(frame_table, text="Table View")
notebook.add(frame_stats, text="Statistics")

# To refresh statistics tab upon any tab changed event
def on_tab_changed(event):
    # Check if current tab is Statistics (3rd tab-index 2)
    if notebook.index(notebook.select()) == 2:
        draw_statistics()

# Bind tab switch to the function
notebook.bind("<<NotebookTabChanged>>", on_tab_changed)

# Frame 1: Home / Add Product UI 
tk.Label(frame_add, text="OptiPick", font=("Helvetica", 20, "bold"), bg=frame_bg, fg="#FF3131").place(x=500, y=50)
tk.Label(frame_add, text="Your own Smart Product Advisior", font=("Helvetica", 18), bg=frame_bg, fg="#FF5757").place(x=450, y=83)
tk.Label(frame_add, text="Add New Product", font=("Helvetica", 18, "bold"), bg=frame_bg, fg="#0288D1").place(x=200, y=120)

entry_name = tk.Entry(frame_add, font=("Helvetica", 14), width=40, bd=2, relief="groove")
entry_price = tk.Entry(frame_add, font=("Helvetica", 14), width=40, bd=2, relief="groove")
entry_budget = tk.Entry(frame_add, font=("Helvetica", 14), width=40, bd=2, relief="groove")
entry_priority = tk.Entry(frame_add, font=("Helvetica", 14), width=40, bd=2, relief="groove")

labels = ["Product Name: ", "Price (₹): ", "Select Features: "]
for i, label in enumerate(labels):
    tk.Label(frame_add, text=label, font=("Helvetica", 14, "bold"), bg=frame_bg, fg="#333333").place(x=200, y=190 + i*60)

tk.Label(frame_add, text="Your Budget (₹): ", font=("Helvetica", 14, "bold"), bg=frame_bg, fg="#333333").place(x=200, y=500)
tk.Label(frame_add, text="Priority Level (1-5):  ", font=("Helvetica", 14, "bold"), bg=frame_bg, fg="#333333").place(x=200, y=550)

entry_name.place(x=420, y=190)
entry_price.place(x=420, y=249)
entry_budget.place(x=420, y=500)
entry_priority.place(x=420, y=550)

feature_vars = {}
feature_frame = tk.Frame(frame_add, bg=frame_bg)
feature_frame.place(x=410, y=308)
for i, feat in enumerate(feature_weights):
    var = tk.BooleanVar()
    chk = tk.Checkbutton(feature_frame, text=feat, variable=var, font=("Helvetica", 12), bg=frame_bg, fg="#333333", selectcolor="#BBDEFB")
    chk.grid(row=i//2, column=i%2, sticky="w", padx=10, pady=5)
    feature_vars[feat] = var

btn_add = tk.Button(frame_add, text="Add Product", font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", bd=0, padx= 5, pady=5, command=add_product)
btn_reco = tk.Button(frame_add, text="Get Recommendation", font=("Helvetica", 12, "bold"), bg="#0288D1", fg="white", bd=0, padx= 5, pady=5, command=lambda: recommend_product(go_to_stats=False))
btn_export = tk.Button(frame_add, text="Export to CSV", font=("Helvetica", 12, "bold"), bg="#FBC02D", fg="white", bd=0, padx= 5, pady=5, command=export_recommendation_csv)
btn_view_stats = tk.Button(frame_add, text="Recommend & View Statistics", font=("Helvetica", 12, "bold"), bg="#7B1FA2", fg="white", bd=0, relief="flat", padx= 5, pady=5, command=lambda: recommend_product(go_to_stats=True))

btn_add.place(x=950, y=249)
btn_reco.place(x=950, y=299)
btn_export.place(x=950, y=349)
btn_view_stats.place(x=950, y=399)

canvas_bg = tk.Canvas(frame_add, width=2000, height=500, bg="#FFDE59", highlightthickness=0)
canvas_bg.place(x=0, y=640)
canvas_bg.create_rectangle(10, 10, 140, 140, fill="#FFDE59", outline="#FFDE59", width=2)

result_label = tk.Label(frame_add, text="No Recommendation yet..", font=("Helvetica", 14), bg="#FFDE59", wraplength=700, justify="left")
result_label.place(x=420, y=700)

canvas_img = tk.Canvas(frame_add, width=300, height=640, bg=frame_bg, highlightthickness=0)
canvas_img.place(x=1250, y=0)
image1 = Image.open("OptiPick_sideBanner.png")
photo = ImageTk.PhotoImage(image1)
canvas_img.create_image(0, 0, image=photo, anchor="nw")  
canvas_img.photo = photo

canvas_img = tk.Canvas(frame_add, width=300, height=640, bg=frame_bg, highlightthickness=0)
canvas_img.place(x=1250, y=650)
image2 = Image.open("OptiPick_sideBanner2.png")
photo = ImageTk.PhotoImage(image2)
canvas_img.create_image(0, 0, image=photo, anchor="nw")  
canvas_img.photo = photo

# Frame 2: Table View
tk.Label(frame_table, text="Product Table", font=("Helvetica", 16, "bold"), bg=frame_bg, fg="#0288D1").pack(pady=12)

table_frame = tk.Frame(frame_table, bg=frame_bg)
table_frame.pack(fill="both", expand=True, padx=24, pady=8)

cols = ("Name", "Price", "Features", "Priority", "Score")
table = ttk.Treeview(table_frame, columns=cols, show="headings", style="Treeview")
for col in cols:
    table.heading(col, text=col)
    table.column(col, width=160 if col != "Score" else 90, anchor="w")
table.pack(fill="both", expand=True)

table_btn_frame = tk.Frame(frame_table, bg=frame_bg)
table_btn_frame.pack(pady=12)

tk.Button(table_btn_frame, text="Delete Product", font=("Helvetica", 11, "bold"), bg="#D32F2F", fg="white", bd=0, relief="flat", command=delete_selected).pack(side="left", padx=6)
tk.Button(table_btn_frame, text="Save Product List", font=("Helvetica", 11, "bold"), bg="#0288D1", fg="white", bd=0, relief="flat", command=save_product_list).pack(side="left", padx=6)
tk.Button(table_btn_frame, text="Load Product List", font=("Helvetica", 11, "bold"), bg="#FBC02D", fg="white", bd=0, relief="flat", command=load_product_list).pack(side="left", padx=6)
tk.Button(table_btn_frame, text="Refresh Table", font=("Helvetica", 11, "bold"), bg="#607D8B", fg="white", bd=0, relief="flat", command=update_table).pack(side="left", padx=6)

# Initial state
notebook.select(frame_add)
root.mainloop()
