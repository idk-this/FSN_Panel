class LogManager:
    _instance = None

    def __new__(cls, textbox=None):
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, textbox=None):
        if self._initialized:
            return
        if textbox is not None:
            #raise ValueError("Textbox must be provided for the first initialization")
            self.textbox = textbox
            self.textbox.configure(state="normal")
            self.textbox.delete("0.0", "end")
            self.textbox.configure(state="disabled")
            self._initialized = True

    def add_log(self, message):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"{message}\n")
        self.textbox.see("end")  # прокрутка вниз
        self.textbox.configure(state="disabled")
