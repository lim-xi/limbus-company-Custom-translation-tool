"""
JS / JSON 文件夹级查找替换工具 - 完整版（带强制保存记录）
- 支持 .js 和 .json 文件
- 行号与编辑区同步滚动
- 文件夹级批量查找替换
- 历史记录保存在程序所在目录的 history.json
- 每次保存文件也会自动记录（用于调试）
- 详细调试日志 debug.log
"""

import os
import sys
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

# ---------- 获取程序所在目录 ----------
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
DEBUG_FILE = os.path.join(BASE_DIR, "debug.log")

def debug_log(msg):
    """写入调试日志"""
    try:
        with open(DEBUG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except:
        pass

def load_history():
    debug_log("load_history 被调用")
    if not os.path.exists(HISTORY_FILE):
        debug_log(f"history.json 不存在，尝试创建：{HISTORY_FILE}")
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            debug_log("创建成功")
        except Exception as e:
            debug_log(f"创建失败：{e}")
            messagebox.showerror("初始化历史失败", f"无法创建 {HISTORY_FILE}：{e}")
        return {}

    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            debug_log(f"成功读取 history.json，内容：{data}")
            return data
    except json.JSONDecodeError:
        debug_log("history.json 内容损坏，重置")
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            messagebox.showwarning("历史文件修复", f"{HISTORY_FILE} 内容损坏，已重置为空。")
        except Exception as e:
            debug_log(f"重置失败：{e}")
            messagebox.showerror("修复失败", f"无法重置 {HISTORY_FILE}：{e}")
        return {}
    except Exception as e:
        debug_log(f"读取失败：{e}")
        messagebox.showerror("读取历史失败", f"无法读取 {HISTORY_FILE}：{e}")
        return {}

def save_history(history):
    debug_log(f"save_history 被调用，路径：{HISTORY_FILE}，记录数：{len(history)}")
    try:
        temp_file = HISTORY_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, HISTORY_FILE)
        debug_log("写入临时文件并重命名成功")

        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        if test_data != history:
            raise Exception("验证失败：写入的数据与内存不一致")
        debug_log("验证通过")
        return True
    except Exception as e:
        debug_log(f"保存失败：{e}")
        messagebox.showerror("保存历史失败", 
            f"无法保存到 {HISTORY_FILE}\n错误：{e}\n\n"
            "请检查文件是否被其他程序占用，或该目录是否有写入权限。")
        return False

# ---------- 主应用 ----------
class CodeEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JS / JSON 编辑器 - 带历史记录")
        self.root.geometry("1200x700")

        debug_log("程序启动")
        self.current_folder = None
        self.current_file = None
        self.current_content = ""
        self.history = load_history()
        debug_log(f"初始化后 history = {self.history}")

        self.create_widgets()

        messagebox.showinfo(
            "历史记录位置",
            f"修改记录将保存在：\n{HISTORY_FILE}\n\n"
            f"调试日志保存在：\n{DEBUG_FILE}\n\n"
            "如果历史未保存，请查看 debug.log。"
        )

    def create_widgets(self):
        toolbar = tk.Frame(self.root, bg='lightgray', height=40)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_open = tk.Button(toolbar, text="📂 打开文件夹", command=self.open_folder)
        btn_open.pack(side=tk.LEFT, padx=5, pady=5)

        btn_find_current = tk.Button(toolbar, text="🔍 当前文件查找", command=self.show_find_replace)
        btn_find_current.pack(side=tk.LEFT, padx=5, pady=5)

        btn_find_folder = tk.Button(toolbar, text="📁 文件夹查找替换", command=self.show_folder_search)
        btn_find_folder.pack(side=tk.LEFT, padx=5, pady=5)

        btn_save = tk.Button(toolbar, text="💾 保存", command=self.save_file)
        btn_save.pack(side=tk.LEFT, padx=5, pady=5)

        btn_import = tk.Button(toolbar, text="📥 导入新版并审查", command=self.import_and_review)
        btn_import.pack(side=tk.LEFT, padx=5, pady=5)

        btn_view_history = tk.Button(toolbar, text="📜 查看历史", command=self.view_history)
        btn_view_history.pack(side=tk.LEFT, padx=5, pady=5)

        btn_debug = tk.Button(toolbar, text="🐛 显示调试信息", command=self.show_debug_info)
        btn_debug.pack(side=tk.LEFT, padx=5, pady=5)

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(paned, width=250)
        paned.add(left_frame, weight=0)

        self.tree = ttk.Treeview(left_frame, show='tree')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        right_frame = tk.Frame(paned)
        paned.add(right_frame, weight=1)

        text_frame = tk.Frame(right_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.line_numbers = tk.Text(text_frame, width=4, padx=3, takefocus=0, border=0,
                                    background='lightgray', state='disabled', wrap='none')
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text = tk.Text(text_frame, wrap='none', undo=True, font=('Consolas', 11),
                            yscrollcommand=scrollbar.set)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.on_scroll)

        self.text.bind('<<Modified>>', self.on_text_modified)
        self.text.bind('<KeyRelease>', self.update_line_numbers)
        self.text.bind('<ButtonRelease-1>', self.update_line_numbers)

        self.text.tag_configure('match', background='yellow')
        self.text.tag_configure('current_match', background='orange')

        self.search_keyword = None

        self.status = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, msg):
        self.status.config(text=msg)
        self.status.update_idletasks()

    def on_scroll(self, *args):
        self.text.yview(*args)
        self.line_numbers.yview(*args)

    # ---------- 文件树操作 ----------
    def open_folder(self):
        folder = filedialog.askdirectory(title="选择包含 JS / JSON 文件的文件夹")
        if not folder:
            return
        self.current_folder = folder
        self.populate_tree(folder)
        self.set_status(f"已打开文件夹：{folder}")
        debug_log(f"打开文件夹：{folder}")

    def populate_tree(self, folder):
        self.tree.delete(*self.tree.get_children())
        root_node = self.tree.insert('', 'end', text=os.path.basename(folder), open=True, tags=('folder',))
        self._add_files(folder, root_node)

    def _add_files(self, path, parent):
        try:
            for item in os.listdir(path):
                full = os.path.join(path, item)
                if os.path.isdir(full):
                    node = self.tree.insert(parent, 'end', text=item, open=False, tags=('folder',))
                    self._add_files(full, node)
                elif item.lower().endswith(('.js', '.json')):
                    self.tree.insert(parent, 'end', text=item, tags=('file', full))
        except PermissionError:
            pass

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        node = selection[0]
        tags = self.tree.item(node, 'tags')
        if 'file' in tags:
            file_path = tags[1]
            self.load_file(file_path)

    def load_file(self, file_path):
        if not os.path.exists(file_path):
            messagebox.showerror("错误", f"文件不存在：{file_path}")
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("读取失败", str(e))
            return

        self.current_file = file_path
        self.current_content = content
        self.text.delete('1.0', tk.END)
        self.text.insert('1.0', content)
        self.text.edit_modified(False)
        self.update_line_numbers()
        self.clear_highlights()
        self.set_status(f"已加载：{os.path.basename(file_path)}")
        debug_log(f"加载文件：{file_path}")

    # ---------- 行号更新 ----------
    def update_line_numbers(self, event=None):
        line_count = int(self.text.index('end-1c').split('.')[0])
        lines = '\n'.join(str(i) for i in range(1, line_count+1))
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)
        self.line_numbers.insert('1.0', lines)
        self.line_numbers.config(state='disabled')

    def on_text_modified(self, event):
        if self.text.edit_modified():
            self.text.edit_modified(False)

    # ---------- 当前文件查找替换 ----------
    def show_find_replace(self):
        if not self.current_file:
            messagebox.showwarning("警告", "请先打开一个文件！")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("当前文件查找替换")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="查找内容：").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        entry_find = tk.Entry(dialog, width=30)
        entry_find.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(dialog, text="替换为：").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        entry_replace = tk.Entry(dialog, width=30)
        entry_replace.grid(row=1, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        def do_find():
            keyword = entry_find.get()
            if not keyword:
                return
            self.search_keyword = keyword
            self.highlight_matches(keyword)
            count = len(self.text.tag_ranges('match')) // 2
            messagebox.showinfo("查找结果", f"找到 {count} 个匹配项")
            self.set_status(f"查找完成，共 {count} 个匹配")

        def replace_current():
            keyword = entry_find.get()
            repl = entry_replace.get()
            if not keyword:
                return
            try:
                index = self.text.index(tk.INSERT)
                ranges = self.text.tag_ranges('match')
                for i in range(0, len(ranges), 2):
                    start = ranges[i]
                    end = ranges[i+1]
                    if self.text.compare(start, '<=', index) and self.text.compare(index, '<=', end):
                        self.text.delete(start, end)
                        self.text.insert(start, repl)
                        self.record_modification(self.current_file, keyword, repl)
                        self.clear_highlights()
                        self.highlight_matches(keyword)
                        self.set_status(f"已替换当前匹配：'{keyword}' → '{repl}'")
                        return
                messagebox.showinfo("提示", "光标不在任何匹配项上")
            except Exception as e:
                debug_log(f"replace_current 异常：{e}")

        def replace_all():
            keyword = entry_find.get()
            repl = entry_replace.get()
            if not keyword:
                return
            content = self.text.get('1.0', tk.END)
            new_content, count = re.subn(re.escape(keyword), repl, content)
            debug_log(f"replace_all: 找到 {count} 处匹配")
            if count == 0:
                messagebox.showinfo("替换", "没有找到匹配项")
                return
            self.text.delete('1.0', tk.END)
            self.text.insert('1.0', new_content)
            debug_log(f"开始记录 {count} 条修改")
            for i in range(count):
                debug_log(f"  记录 #{i+1}")
                self.record_modification(self.current_file, keyword, repl)
            self.clear_highlights()
            messagebox.showinfo("替换完成", f"已替换 {count} 处")
            self.set_status(f"全部替换完成，共 {count} 处")

        tk.Button(btn_frame, text="查找全部", command=do_find).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="替换当前", command=replace_current).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="全部替换", command=replace_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def highlight_matches(self, keyword):
        self.clear_highlights()
        if not keyword:
            return
        start = '1.0'
        while True:
            pos = self.text.search(keyword, start, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(keyword)}c"
            self.text.tag_add('match', pos, end)
            start = end

    def clear_highlights(self):
        self.text.tag_remove('match', '1.0', tk.END)
        self.text.tag_remove('current_match', '1.0', tk.END)

    # ---------- 文件夹级查找替换 ----------
    def show_folder_search(self):
        if not self.current_folder:
            messagebox.showwarning("警告", "请先打开一个文件夹！")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("文件夹查找替换")
        dialog.geometry("800x500")
        dialog.transient(self.root)
        dialog.grab_set()

        top_frame = tk.Frame(dialog)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(top_frame, text="查找内容：").pack(side=tk.LEFT)
        entry_find = tk.Entry(top_frame, width=30)
        entry_find.pack(side=tk.LEFT, padx=5)

        tk.Label(top_frame, text="替换为：").pack(side=tk.LEFT, padx=(10,0))
        entry_replace = tk.Entry(top_frame, width=30)
        entry_replace.pack(side=tk.LEFT, padx=5)

        case_var = tk.BooleanVar(value=False)
        tk.Checkbutton(top_frame, text="区分大小写", variable=case_var).pack(side=tk.LEFT, padx=10)

        btn_search = tk.Button(top_frame, text="搜索", command=lambda: self.do_folder_search(
            entry_find.get(), case_var.get(), result_tree, dialog, entry_replace))
        btn_search.pack(side=tk.LEFT, padx=5)

        btn_close = tk.Button(top_frame, text="关闭", command=dialog.destroy)
        btn_close.pack(side=tk.LEFT, padx=5)

        result_frame = tk.Frame(dialog)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = tk.Scrollbar(result_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        result_tree = ttk.Treeview(result_frame, columns=('file', 'line', 'content'),
                                   show='tree headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=result_tree.yview)

        result_tree.heading('#0', text='匹配项')
        result_tree.heading('file', text='文件')
        result_tree.heading('line', text='行号')
        result_tree.heading('content', text='匹配行内容')

        result_tree.column('#0', width=30)
        result_tree.column('file', width=200)
        result_tree.column('line', width=60)
        result_tree.column('content', width=400)

        result_tree.pack(fill=tk.BOTH, expand=True)

        result_tree.bind('<Double-Button-1>', lambda e: self.on_result_double_click(result_tree))

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        def replace_selected():
            selected = result_tree.selection()
            if not selected:
                messagebox.showinfo("提示", "请先选择要替换的匹配项")
                return
            keyword = entry_find.get()
            repl = entry_replace.get()
            if not keyword:
                return
            for item in selected:
                values = result_tree.item(item, 'values')
                if not values:
                    continue
                file_path, line_num, line_content = values[0], int(values[1]), values[2]
                self.replace_in_file(file_path, keyword, repl, line_num, line_content)
            self.do_folder_search(keyword, case_var.get(), result_tree, dialog, entry_replace, keep_dialog=True)

        def replace_all_folder():
            keyword = entry_find.get()
            repl = entry_replace.get()
            if not keyword:
                return
            all_items = result_tree.get_children('')
            if not all_items:
                messagebox.showinfo("提示", "没有匹配项")
                return
            file_matches = {}
            for item in all_items:
                values = result_tree.item(item, 'values')
                if not values:
                    continue
                file_path, line_num, line_content = values[0], int(values[1]), values[2]
                if file_path not in file_matches:
                    file_matches[file_path] = []
                file_matches[file_path].append((line_num, line_content))
            total_replaced = 0
            for file_path, matches in file_matches.items():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except Exception as e:
                    messagebox.showerror("读取失败", f"无法读取 {file_path}: {e}")
                    continue
                modified = False
                for line_num, _ in matches:
                    idx = line_num - 1
                    if 0 <= idx < len(lines):
                        if re.search(re.escape(keyword), lines[idx], flags=0 if case_var.get() else re.I):
                            new_line = re.sub(re.escape(keyword), repl, lines[idx], flags=0 if case_var.get() else re.I)
                            lines[idx] = new_line
                            modified = True
                            total_replaced += 1
                if modified:
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        for line_num, _ in matches:
                            self.record_modification(file_path, keyword, repl)
                    except Exception as e:
                        messagebox.showerror("保存失败", f"保存 {file_path} 失败: {e}")
            messagebox.showinfo("替换完成", f"共替换了 {total_replaced} 处")
            self.set_status(f"文件夹替换完成，共 {total_replaced} 处")
            self.do_folder_search(keyword, case_var.get(), result_tree, dialog, entry_replace, keep_dialog=True)

        tk.Button(btn_frame, text="替换选中", command=replace_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="全部替换（文件夹）", command=replace_all_folder).pack(side=tk.LEFT, padx=5)

    def do_folder_search(self, keyword, case_sensitive, result_tree, dialog, entry_replace, keep_dialog=False):
        for item in result_tree.get_children(''):
            result_tree.delete(item)
        if not keyword:
            return
        files = self.collect_files(self.current_folder)
        total_matches = 0
        flags = 0 if case_sensitive else re.I
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except:
                continue
            for line_num, line in enumerate(lines, start=1):
                if re.search(keyword, line, flags=flags):
                    display_line = line.rstrip('\n')
                    if len(display_line) > 80:
                        display_line = display_line[:77] + '...'
                    result_tree.insert('', 'end', text=str(total_matches+1),
                                       values=(file_path, line_num, display_line))
                    total_matches += 1
        if total_matches > 0:
            messagebox.showinfo("搜索结果", f"找到 {total_matches} 个匹配项")
        else:
            messagebox.showinfo("搜索结果", "未找到匹配项")

    def collect_files(self, folder):
        files = []
        for root, dirs, filenames in os.walk(folder):
            for fname in filenames:
                if fname.lower().endswith(('.js', '.json')):
                    files.append(os.path.join(root, fname))
        return files

    def replace_in_file(self, file_path, keyword, repl, line_num, line_content):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            messagebox.showerror("读取失败", str(e))
            return
        idx = line_num - 1
        if 0 <= idx < len(lines):
            old_line = lines[idx]
            new_line = re.sub(re.escape(keyword), repl, old_line, count=1, flags=re.I)
            if new_line != old_line:
                lines[idx] = new_line
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    self.record_modification(file_path, keyword, repl)
                    messagebox.showinfo("替换成功", f"已替换文件 {os.path.basename(file_path)} 第 {line_num} 行")
                    self.set_status(f"已替换 {os.path.basename(file_path)} 第 {line_num} 行")
                except Exception as e:
                    messagebox.showerror("保存失败", str(e))
            else:
                messagebox.showinfo("提示", "该行已不包含关键词（可能被修改）")
        else:
            messagebox.showerror("错误", "行号超出范围")

    def on_result_double_click(self, result_tree):
        selected = result_tree.selection()
        if not selected:
            return
        item = selected[0]
        values = result_tree.item(item, 'values')
        if not values:
            return
        file_path, line_num, _ = values[0], int(values[1]), values[2]
        self.load_file(file_path)
        self.text.mark_set(tk.INSERT, f"{line_num}.0")
        self.text.see(tk.INSERT)
        self.text.tag_remove('highlight', '1.0', tk.END)
        self.text.tag_configure('highlight', background='lightblue')
        self.text.tag_add('highlight', f"{line_num}.0", f"{line_num}.end")

    # ---------- 修改记录（核心） ----------
    def record_modification(self, file_path, old_text, new_text):
        debug_log(f"record_modification 被调用: file={file_path}, old='{old_text}', new='{new_text}'")
        abs_path = os.path.abspath(file_path)
        debug_log(f"  绝对路径: {abs_path}")
        if abs_path not in self.history:
            self.history[abs_path] = []
            debug_log(f"  创建新条目: {abs_path}")
        self.history[abs_path].append({
            'old': old_text,
            'new': new_text,
            'time': datetime.now().isoformat()
        })
        debug_log(f"  当前 history 内容: {self.history}")

        success = save_history(self.history)
        if success:
            self.set_status(f"✅ 已记录修改：'{old_text}' → '{new_text}' (共 {len(self.history)} 条记录)")
            messagebox.showinfo(
                "历史记录已保存",
                f"修改已成功写入：\n{HISTORY_FILE}\n\n"
                f"当前共 {len(self.history)} 个文件有修改记录。"
            )
        else:
            self.history[abs_path].pop()
            if not self.history[abs_path]:
                del self.history[abs_path]
            debug_log("保存失败，已回滚")
            messagebox.showerror("记录失败", "修改未被记录，请检查磁盘空间或权限。")
        return success

    # ---------- 查看历史 ----------
    def view_history(self):
        debug_log("view_history 被调用，当前 self.history = " + str(self.history))
        if not self.history:
            messagebox.showinfo("历史记录", "当前没有任何修改记录。")
            return

        lines = []
        for file_path, records in self.history.items():
            lines.append(f"📄 {os.path.basename(file_path)} ({len(records)} 条)")
            for idx, rec in enumerate(records, 1):
                lines.append(f"   {idx}. '{rec['old']}' → '{rec['new']}'  {rec['time']}")
            lines.append("")
        text = "\n".join(lines)

        dialog = tk.Toplevel(self.root)
        dialog.title("历史记录内容")
        dialog.geometry("600x400")
        text_widget = tk.Text(dialog, wrap='none')
        text_widget.pack(fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(text_widget)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)
        text_widget.insert('1.0', text)
        text_widget.config(state='disabled')

        messagebox.showinfo("历史文件位置", f"历史数据保存在：\n{HISTORY_FILE}")

    # ---------- 显示调试信息 ----------
    def show_debug_info(self):
        info = f"程序目录: {BASE_DIR}\n"
        info += f"历史文件: {HISTORY_FILE}\n"
        info += f"调试日志: {DEBUG_FILE}\n"
        info += f"history 内容: {self.history}\n"
        info += f"history 是否为空: {not bool(self.history)}"
        messagebox.showinfo("调试信息", info)

    # ---------- 保存当前文件（强制记录保存操作） ----------
    def save_file(self):
        if not self.current_file:
            messagebox.showwarning("警告", "没有打开的文件")
            return
        content = self.text.get('1.0', tk.END)
        if content.endswith('\n'):
            content = content[:-1]
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.current_content = content
            # 强制记录一次“保存”操作（用于测试写入功能）
            self.record_modification(self.current_file, "(保存文件)", "(文件已保存)")
            messagebox.showinfo("成功", f"已保存 {os.path.basename(self.current_file)}")
            self.set_status(f"已保存 {os.path.basename(self.current_file)}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    # ---------- 导入新版并审查 ----------
    def import_and_review(self):
        if not self.current_folder:
            folder = filedialog.askdirectory(title="选择包含最新 JS / JSON 文件的文件夹")
            if not folder:
                return
            self.current_folder = folder
        else:
            folder = filedialog.askdirectory(title="选择最新文件夹（留空使用当前）", initialdir=self.current_folder)
            if folder:
                self.current_folder = folder

        self.populate_tree(self.current_folder)

        if not self.history:
            messagebox.showinfo("无记录", "没有历史修改记录。")
            return

        files_to_review = []
        for file_path in self.history.keys():
            base = os.path.basename(file_path)
            found = self.find_file_in_tree(base)
            if found:
                files_to_review.append((file_path, found))

        if not files_to_review:
            messagebox.showinfo("无匹配", "历史记录中的文件在当前文件夹中未找到。")
            return

        result_dialog = tk.Toplevel(self.root)
        result_dialog.title("审查结果")
        result_dialog.geometry("700x500")
        result_text = tk.Text(result_dialog, wrap='none')
        result_text.pack(fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(result_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        result_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=result_text.yview)

        result_text.insert(tk.END, "📋 审查报告\n")
        result_text.insert(tk.END, "=" * 50 + "\n\n")

        for old_path, new_path in files_to_review:
            result_text.insert(tk.END, f"📄 文件：{os.path.basename(new_path)}\n")
            result_text.insert(tk.END, f"   旧路径：{old_path}\n")
            result_text.insert(tk.END, f"   新路径：{new_path}\n")
            success = self.apply_modifications_to_file(old_path, new_path, result_text)
            if success:
                result_text.insert(tk.END, "   ✅ 已处理\n\n")
            else:
                result_text.insert(tk.END, "   ⚠️ 无变化或跳过\n\n")
        result_text.insert(tk.END, "=" * 50 + "\n")
        result_text.insert(tk.END, "✅ 审查完成！\n")
        result_text.config(state='disabled')

        if self.current_file:
            self.load_file(self.current_file)
        self.set_status("审查完成")

    def find_file_in_tree(self, filename):
        def search_children(parent):
            for child in self.tree.get_children(parent):
                tags = self.tree.item(child, 'tags')
                if 'file' in tags and os.path.basename(tags[1]) == filename:
                    return tags[1]
                if 'folder' in tags:
                    result = search_children(child)
                    if result:
                        return result
            return None
        return search_children('')

    def apply_modifications_to_file(self, old_path, new_path, result_text=None):
        if old_path not in self.history:
            return False
        modifications = self.history[old_path]
        if not modifications:
            return False

        try:
            with open(new_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            if result_text:
                result_text.insert(tk.END, f"   ❌ 读取失败：{e}\n")
            return False

        changed = False
        for idx, mod in enumerate(modifications, 1):
            old_text = mod['old']
            new_text = mod['new']
            count = content.count(old_text)
            if result_text:
                result_text.insert(tk.END, f"   📝 修改 #{idx}：'{old_text}' → '{new_text}'\n")
                result_text.insert(tk.END, f"      匹配次数：{count}\n")
            if count == 0:
                if result_text:
                    result_text.insert(tk.END, "      ⏭️ 未找到匹配，跳过\n")
                continue
            elif count == 1:
                content = content.replace(old_text, new_text, 1)
                changed = True
                if result_text:
                    result_text.insert(tk.END, "      ✅ 自动替换成功\n")
            else:
                if result_text:
                    result_text.insert(tk.END, f"      ⚠️ 出现 {count} 次，需要您确认\n")
                resp = messagebox.askyesno(
                    "多处匹配",
                    f"在文件 {os.path.basename(new_path)} 中，\n"
                    f"文本 '{old_text}' 出现了 {count} 次。\n"
                    f"是否全部替换为 '{new_text}'？"
                )
                if resp:
                    content = content.replace(old_text, new_text)
                    changed = True
                    if result_text:
                        result_text.insert(tk.END, "      ✅ 全部替换成功\n")
                else:
                    if result_text:
                        result_text.insert(tk.END, "      ⏭️ 用户跳过\n")

        if changed:
            if messagebox.askyesno("保存修改", f"文件 {os.path.basename(new_path)} 已应用修改，是否保存？"):
                try:
                    with open(new_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    if result_text:
                        result_text.insert(tk.END, "      💾 已保存\n")
                    return True
                except Exception as e:
                    if result_text:
                        result_text.insert(tk.END, f"      ❌ 保存失败：{e}\n")
                    return False
            else:
                if result_text:
                    result_text.insert(tk.END, "      ⏭️ 用户取消保存\n")
                return False
        else:
            if result_text:
                result_text.insert(tk.END, "      ℹ️ 无变化\n")
            return False

# ---------- 启动 ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = CodeEditorApp(root)
    root.mainloop()