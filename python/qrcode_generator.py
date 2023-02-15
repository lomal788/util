import tkinter as tk
from tkinter import ttk
import qrcode
from tkinter import filedialog
from PIL import Image, ImageTk

root = tk.Tk()
root.title("QR코드 생성기")

def TextBoxUpdate(*args):
    val = dropdown_val.get()
    hideAll()

    if val == "URL":
        url_label.pack(side=tk.LEFT, padx=5, pady=5)
        url_entry.pack(side=tk.LEFT, padx=5, pady=5)
    if val == "File":
        file_label.pack(side=tk.LEFT, padx=5, pady=5)
        file_button.pack(side=tk.LEFT, padx=5, pady=5)
    if val == "Text":
        print("text")
        # url_label.pack(side=tk.LEFT, padx=5, pady=5)
        # url_entry.pack(side=tk.LEFT, padx=5, pady=5)
    if val == "Wi-Fi":
        wifi_label.pack(side=tk.LEFT, padx=5, pady=5)
        wifi_entry.pack(side=tk.LEFT, padx=5, pady=5)
    if val == "Bluetooth":
        bluetooth_label.pack(side=tk.LEFT, padx=5, pady=5)
        bluetooth_entry.pack(side=tk.LEFT, padx=5, pady=5)

def hideAll():
    url_label.pack_forget()
    url_entry.pack_forget()
    file_label.pack_forget()
    file_button.pack_forget()
    wifi_label.pack_forget()
    wifi_entry.pack_forget()
    bluetooth_label.pack_forget()
    bluetooth_entry.pack_forget()



def create_qr():
    url = url_entry.get().strip()
    file = file_entry.get().strip()
    wifi = wifi_entry.get().strip()
    bluetooth = bluetooth_entry.get().strip()

    qr_data = ""
    if url:
        qr_data += "url:" + url + "\n"
    if file:
        qr_data += "file:" + file + "\n"
    if wifi:
        qr_data += "wifi:" + wifi + "\n"
    if bluetooth:
        qr_data += "bluetooth:" + bluetooth + "\n"

    if qr_data:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        qr_img = ImageTk.PhotoImage(img)
        qr_canvas.create_image(0, 0, image=qr_img, anchor=tk.NW)
        qr_canvas.image = qr_img
        img_width, img_height = img.size

        qr_canvas.config(width=img_width, height=img_height)

def select_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, file_path)

def save_qr():
    filename = filedialog.asksaveasfilename(defaultextension="."+download_type.get())
    if filename:
        url = url_entry.get().strip()
        file = file_entry.get().strip()
        wifi = wifi_entry.get().strip()
        bluetooth = bluetooth_entry.get().strip()

        qr_data = ""
        if url:
            qr_data += "url:" + url
        if file:
            qr_data += "file:" + file
        if wifi:
            wifi_data = wifi_entry.get().split(",")
            qr_data = f"WIFI:S:{wifi_data[0]};T:{wifi_data[1]};P:{wifi_data[2]};H:{wifi_data[3]};"
        if bluetooth:
            qr_data += "bluetooth:" + bluetooth



        if qr_data:
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # thub_img = Image.open(thub_img_path)
            # thub_img.thumbnail((60, 60))
            # img = qr.make_image().convert('RGB')
            # pos = ((img.size[0]-thub_img.size[0])// 2, (img.size[1]-thub_img.size[1])//2)
            # img.paste(thub_img, pos)

            img.save(filename)

file_button = tk.Button(root, text="Select File", command=select_file)

qr_canvas = tk.Canvas(root, width=200, height=200)
qr_canvas.pack()

type_label = tk.Label(root, text="저장 타입:")
type_label.pack()
download_type = tk.StringVar()
type_options = ["jpg", "png"]
type_dropdown = ttk.Combobox(root, textvariable=download_type, values=type_options, state="readonly")
type_dropdown.pack()
type_dropdown.current(0)

generate_button = tk.Button(root, text="Generate QR Code", command=create_qr)
generate_button.pack()
download_button = tk.Button(root, text="Download QR Code", command=save_qr)
download_button.pack()

input_type_label = tk.Label(root, text="Type:")
input_type_label.pack()

type_label = tk.Label(root, text="Type:")
dropdown_val = tk.StringVar()
type_options = ["URL", "File", "Text", "Wi-Fi", "Bluetooth"]
type_dropdown = ttk.Combobox(root, textvariable=dropdown_val, values=type_options, state="readonly")
type_dropdown.pack()
type_dropdown.current(0)
type_dropdown.bind("<<ComboboxSelected>>", TextBoxUpdate)

url_label = tk.Label(root, text="URL:")
url_label.pack()
url_entry = tk.Entry(root)
url_entry.pack()
file_label = tk.Label(root, text="File:")
file_entry = tk.Entry(root)
wifi_label = tk.Label(root, text="Wi-Fi:")
wifi_entry = tk.Entry(root)
bluetooth_label = tk.Label(root, text="Bluetooth:")
bluetooth_entry = tk.Entry(root)
root.mainloop()
