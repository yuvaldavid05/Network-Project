import socket
import threading
import queue
import tkinter as tk
from tkinter import messagebox

SERVER_IP = "127.0.0.1"
PORT = 5000


class ChatClientGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Chat Client")
        self.root.geometry("820x560")
        self.root.configure(bg="#0b1220")  

        self.sock = None
        self.reader = None
        self.inbox = queue.Queue()
        self.alive = True
        self.my_name = None
        self.current_peer = None

        self.build_ui()
        self.connect_and_handshake()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(60, self.process_inbox)


    def build_ui(self):
        header = tk.Frame(self.root, bg="#0b1220")
        header.pack(fill="x", padx=14, pady=(14, 10))

        self.title_var = tk.StringVar(value="Disconnected")
        tk.Label(
            header, textvariable=self.title_var,
            fg="#e8eefc", bg="#0b1220",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        self.peer_var = tk.StringVar(value="")
        tk.Label(
            header, textvariable=self.peer_var,
            fg="#9fb2d9", bg="#0b1220",
            font=("Segoe UI", 11)
        ).pack(side="left", padx=(12, 0))

       
        self.canvas = tk.Canvas(self.root, bg="#0b1220", highlightthickness=0)
        self.scroll = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)

        self.scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=(0, 12))

        self.msg_frame = tk.Frame(self.canvas, bg="#0b1220")
        self.window_id = self.canvas.create_window((0, 0), window=self.msg_frame, anchor="nw")

        self.msg_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        
        bottom = tk.Frame(self.root, bg="#0b1220")
        bottom.pack(fill="x", padx=14, pady=(0, 14))

        self.entry = tk.Entry(
            bottom, font=("Segoe UI", 12),
            bg="#121b30", fg="#e8eefc",
            insertbackground="#e8eefc", relief="flat"
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        self.entry.bind("<Return>", lambda e: self.send_current())

        self.send_btn = tk.Button(
            bottom, text="Send", command=self.send_current,
            bg="#2f6bff", fg="white",
            activebackground="#2a5fe6", activeforeground="white",
            relief="flat", padx=18, pady=8,
            font=("Segoe UI", 11, "bold")
        )
        self.send_btn.pack(side="left")

        hint = tk.Label(
            self.root,
            text="Commands: /chat Bob | /leave | /bye | Bob:hello | plain message to current peer",
            fg="#7f95c2", bg="#0b1220", font=("Segoe UI", 10)
        )
        hint.pack(fill="x", padx=14, pady=(0, 10))

    def _on_frame_configure(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(1.0)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    
    def set_status(self, text: str):
        self.title_var.set(text)

    def set_peer(self, peer: str | None):
        self.current_peer = peer
        if peer:
            self.peer_var.set(f"• chatting with {peer}")
        else:
            self.peer_var.set("")

    def bubble(self, text: str, kind: str):
        """
        kind: "me" | "peer" | "system"
        """
        row = tk.Frame(self.msg_frame, bg="#0b1220")
        row.pack(fill="x", pady=6, padx=8)

        if kind == "me":
            bg = "#2f6bff"
            fg = "white"
            side = "e"
            padx = (160, 10)
        elif kind == "peer":
            bg = "#1b2a4a"
            fg = "#e8eefc"
            side = "w"
            padx = (10, 160)
        else:
            bg = "#0f1a33"
            fg = "#9fb2d9"
            side = "c"
            padx = (80, 80)

        bubble = tk.Label(
            row, text=text,
            bg=bg, fg=fg,
            font=("Segoe UI", 11),
            justify="left", wraplength=520,
            padx=12, pady=8
        )
        bubble.pack(anchor=side, padx=padx)

        self.root.update_idletasks()
        self.canvas.yview_moveto(1.0)

    
    def prompt(self, title: str) -> str:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg="#0b1220")
        dialog.resizable(False, False)

        
        dialog.transient(self.root)
        dialog.lift()
        dialog.grab_set()
        dialog.focus_force()
        dialog.attributes("-topmost", True)  

        
        self.root.update_idletasks()
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        w, h = 360, 150
        x = rx + (rw - w) // 2
        y = ry + (rh - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(
            dialog,
            text=title,
            fg="#e8eefc",
            bg="#0b1220",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(16, 8))

        ent = tk.Entry(
            dialog,
            font=("Segoe UI", 12),
            bg="#121b30",
            fg="#e8eefc",
            insertbackground="#e8eefc",
            relief="flat"
        )
        ent.pack(padx=16, fill="x", ipady=8)
        ent.focus_set()

        result = {"v": ""}

        def ok():
            result["v"] = ent.get().strip()
            dialog.destroy()

        btn = tk.Button(
            dialog,
            text="OK",
            command=ok,
            bg="#2f6bff",
            fg="white",
            activebackground="#2a5fe6",
            relief="flat",
            padx=18,
            pady=8,
            font=("Segoe UI", 11, "bold")
        )
        btn.pack(pady=14)

        dialog.bind("<Return>", lambda e: ok())

        
        dialog.after(150, lambda: dialog.attributes("-topmost", False))

        self.root.wait_window(dialog)
        return result["v"]

   
    def connect_and_handshake(self):
        self.my_name = self.prompt("Enter your name")
        if not self.my_name:
            self.root.after(0, self.root.destroy)
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_IP, PORT))
            self.reader = self.sock.makefile("r", encoding="utf-8", newline="\n")

            self.set_status(f"Connected as {self.my_name}")
            self.bubble("[SYSTEM] Connected. Use /chat <name> to start.", "system")

            threading.Thread(target=self.recv_loop, daemon=True).start()
            self.sock.sendall((self.my_name + "\n").encode("utf-8"))

        except Exception as e:
            messagebox.showerror("Connection error", f"Failed to connect: {e}")
            self.root.after(0, self.root.destroy)

    def recv_loop(self):
        try:
            while self.alive:
                line = self.reader.readline()
                if not line:
                    self.inbox.put(("DISCONNECT", None))
                    break
                self.inbox.put(("LINE", line.strip()))
        except Exception:
            self.inbox.put(("DISCONNECT", None))
        finally:
            try:
                if self.sock:
                    self.sock.close()
            except Exception:
                pass

    def process_inbox(self):
        try:
            while True:
                kind, payload = self.inbox.get_nowait()

                if kind == "LINE":
                    line = payload

                    
                    if line.startswith("PEER_LEFT "):
                        peer = line.split(" ", 1)[1].strip()
                        self.bubble(f"[SYSTEM] {peer} left the chat.", "system")
                        self.set_peer(None)
                        messagebox.showinfo("Chat ended", f"{peer} closed the chat / disconnected.")
                        continue

                   
                    if line.startswith("CHAT_STARTED "):
                        peer = line.split(" ", 1)[1].strip()
                        self.set_peer(peer)
                        self.bubble(f"[SYSTEM] Chat started with {peer}.", "system")
                        continue

                    
                    if line.startswith("FROM "):
                        self.bubble(line, "peer")
                        continue

                    
                    self.bubble(line, "system")

                elif kind == "DISCONNECT":
                    self.bubble("[SYSTEM] Server disconnected.", "system")
                    messagebox.showwarning("Disconnected", "Server disconnected / connection lost.")
                    self.set_status("Disconnected")
                    self.set_peer(None)
        except queue.Empty:
            pass

        if self.alive:
            self.root.after(60, self.process_inbox)

    def send_current(self):
        msg = self.entry.get().strip()
        if not msg:
            return
        self.entry.delete(0, "end")

        
        self.bubble(f"ME: {msg}", "me")

        
        if msg.lower().startswith("/chat "):
            target = msg[6:].strip()
            if target:
                self.set_peer(target)

        try:
            self.sock.sendall((msg + "\n").encode("utf-8"))
        except Exception:
            self.bubble("[SYSTEM] Failed to send (connection lost).", "system")
            messagebox.showwarning("Send failed", "Failed to send (connection lost).")

        if msg.lower() in ("/bye", "bye", "exit"):
            self.on_close()

    def on_close(self):
        if not self.alive:
            return
        self.alive = False
        try:
            if self.sock:
                try:
                    self.sock.sendall(b"/bye\n")
                except Exception:
                    pass
                try:
                    self.sock.close()
                except Exception:
                    pass
        finally:
            self.root.destroy()


def main():
    root = tk.Tk()
    ChatClientGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
