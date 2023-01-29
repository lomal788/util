import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from Crypto.Cipher import AES
import tkinter.simpledialog as tk_simple_dialog
import re
import hashlib

BS = 16
pad = lambda s: s + (BS - len(s.encode('utf-8')) % BS) * chr(BS - len(s.encode('utf-8')) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]

def get_key_and_iv():
    key = tk_simple_dialog.askstring("Encryption Key", "비밀번호를 입력해주세요. 32자 이상 :")
    if len(key) < 32:
        messagebox.showinfo("오류", "비밀번호는 32자 이상 이여야 됩니다.")
        raise ValueError("비밀번호는 32자 이상 이여야 됩니다.")
    elif re.search('[a-zA-Z]+', key) is None:
        messagebox.showinfo("오류", "비밀번호는 최소 1개 이상의 영문 대소문자가 포함되어야 함.")
        raise ValueError("비밀번호는 최소 1개 이상의 영문 대소문자가 포함되어야 함.")
    elif re.search('[`~!@#$%^&*(),<.>/?]+', key) is None:
        messagebox.showinfo("오류", "비밀번호는 최소 1개 이상의 특수문자가 포함되어야 함.")
        raise ValueError("비밀번호는 최소 1개 이상의 특수문자가 포함되어야 함.")
    
    iv = key[:16]
    key = hashlib.sha256(key.encode()).hexdigest()
    key = key[:32]

    return key.encode(), iv.encode()

def open_file():
    file_path = filedialog.askopenfilename(filetypes=(("enc", "*.enc"),("enc", "*.enc")))
    if file_path == "":
        return
    key, iv = get_key_and_iv()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    with open(file_path, "rb") as file:
        encrypted_contents = file.read()
        decrypted_contents = cipher.decrypt(encrypted_contents).rstrip().decode()
        text.insert('1.0', unpad(decrypted_contents))

def save_file():
    file_path = filedialog.asksaveasfilename(defaultextension='.enc')
    if file_path == "":
        return
    key, iv = get_key_and_iv()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    contents = text.get('1.0', 'end')
    contents = pad(contents)

    encrypted_contents = cipher.encrypt(contents.encode())
    with open(file_path, "wb") as file:
        file.write(encrypted_contents)

def quit_app():
    if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
        root.destroy()

root = tk.Tk()
root.title("Notepad")
root.bind("<Control-s>", lambda event: save_file())

text = tk.Text(root, wrap='word')
text.pack(expand='yes', fill='both')

menu = tk.Menu(root)
root.config(menu=menu)

file_menu = tk.Menu(menu)
menu.add_cascade(label='File', menu=file_menu)
file_menu.add_command(label='Open...', command=open_file)
file_menu.add_command(label='Save...', command=save_file)
file_menu.add_separator()
file_menu.add_command(label='Quit', command=quit_app)

root.mainloop()

root.mainloop(

root.mainloop

root.mainloo

root.mainlo

root.mainl

import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from Crypto.Cipher import AES
import tkinter.simpledialog as tk_simple_dialog
import re
import hashlib

BS = 16
pad = lambda s: s + (BS - len(s.encode('utf-8')) % BS) * chr(BS - len(s.encode('utf-8')) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]

def get_key_and_iv():
    key = tk_simple_dialog.askstring("Encryption Key", "비밀번호를 입력해주세요. 32자 이상 :")
    if len(key) < 32:
        messagebox.showinfo("오류", "비밀번호는 32자 이상 이여야 됩니다.")
        raise ValueError("비밀번호는 32자 이상 이여야 됩니다.")
    elif re.search('[a-zA-Z]+', key) is None:
        messagebox.showinfo("오류", "비밀번호는 최소 1개 이상의 영문 대소문자가 포함되어야 함.")
        raise ValueError("비밀번호는 최소 1개 이상의 영문 대소문자가 포함되어야 함.")
    elif re.search('[`~!@#$%^&*(),<.>/?]+', key) is None:
        messagebox.showinfo("오류", "비밀번호는 최소 1개 이상의 특수문자가 포함되어야 함.")
        raise ValueError("비밀번호는 최소 1개 이상의 특수문자가 포함되어야 함.")
    
    iv = key[:16]
    key = hashlib.sha256(key.encode()).hexdigest()
    key = key[:32]

    return key.encode(), iv.encode()

def open_file():
    file_path = filedialog.askopenfilename(filetypes=(("enc", "*.enc"),("enc", "*.enc")))
    if file_path == "":
        return
    key, iv = get_key_and_iv()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    with open(file_path, "rb") as file:
        encrypted_contents = file.read()
        decrypted_contents = cipher.decrypt(encrypted_contents).rstrip().decode()
        text.insert('1.0', unpad(decrypted_contents))

def save_file():
    file_path = filedialog.asksaveasfilename(defaultextension='.enc')
    if file_path == "":
        return
    key, iv = get_key_and_iv()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    contents = text.get('1.0', 'end')
    contents = pad(contents)

    encrypted_contents = cipher.encrypt(contents.encode())
    with open(file_path, "wb") as file:
        file.write(encrypted_contents)

def quit_app():
    if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
        root.destroy()

root = tk.Tk()
root.title("Notepad")
root.bind("<Control-s>", lambda event: save_file())

text = tk.Text(root, wrap='word')
text.pack(expand='yes', fill='both')

menu = tk.Menu(root)
root.config(menu=menu)

file_menu = tk.Menu(menu)
menu.add_cascade(label='File', menu=file_menu)
file_menu.add_command(label='Open...', command=open_file)
file_menu.add_command(label='Save...', command=save_file)
file_menu.add_separator()
file_menu.add_command(label='Quit', command=quit_app)

root.mainloop()
