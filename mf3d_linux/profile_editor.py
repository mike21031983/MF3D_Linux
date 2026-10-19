"""Standalone native MF3D profile editor; NO transmission of device settings."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from .device_profile import Profile,SETTINGS,PALETTE
class ProfileEditor:
    def __init__(self,parent,profile=None):
        self.win=tk.Toplevel(parent)
        self.win.title('MIDI Fighter 3D — локальный профиль')
        self.win.geometry('820x690')
        self.profile=profile if profile is not None else Profile()
        self.vars={};self.flag_vars=[]
        self.bank=0;self.pad=0
        self.color_state=tk.StringVar(value='inactive')
        self.footer=tk.StringVar(value='Никаких изменений в контроллер не отправляется')
        self.build()
        self.win.protocol('WM_DELETE_WINDOW',self.win.destroy)
    def build(self):
        body=ttk.Frame(self.win,padding=12)
        body.pack(fill='both',expand=True)
        ttk.Label(body,text='MIDI Fighter 3D — настройки',font=('Sans',17,'bold')).pack(anchor='w')
        ttk.Label(body,text='Профиль на компьютере. Запись в контроллер отключена до проверки SysEx-протокола.').pack(anchor='w')
        tabs=ttk.Notebook(body)
        tabs.pack(fill='both',expand=True,pady=9)
        for title,page in [('Общие','settings'),('Движение','motion')]:
            pane=ttk.Frame(tabs,padding=15)
            tabs.add(pane,text=title)
            for row,s in enumerate(x for x in SETTINGS if x.page==page):
                ttk.Label(pane,text=s.label or s.key,width=32).grid(row=row,column=0,sticky='w',pady=6)
                value=tk.IntVar(value=self.profile.settings[s.key])
                self.vars[s.key]=value
                if s.kind=='enum':
                    widget=ttk.Combobox(pane,state='readonly',values=s.options,width=30)
                    widget.current(value.get())
                    widget.bind('<<ComboboxSelected>>',lambda evt,k=s.key,w=widget:self.vars[k].set(w.current()))
                elif s.kind=='bool':
                    widget=ttk.Checkbutton(pane,variable=value)
                elif s.kind=='bitflag':
                    widget=ttk.Frame(pane)
                    for i,option in enumerate(s.options):
                        b=tk.BooleanVar(value=bool(value.get()&(1<<i)))
                        self.flag_vars.append(b)
                        ttk.Checkbutton(widget,text=option,variable=b).pack(side='left',padx=4)
                        b.trace_add('write',lambda *_ ,k=s.key,n=i,v=b:self.change_flag(k,n,v.get()))
                else:
                    widget=ttk.Spinbox(pane,from_=s.minimum,to=s.maximum,width=10,textvariable=value)
                widget.grid(row=row,column=1,sticky='w',pady=6)
        colors=ttk.Frame(tabs,padding=12)
        tabs.add(colors,text='Подсветка 4×16')
        self.make_colors(colors)
        actions=ttk.Frame(body)
        actions.pack(anchor='w')
        ttk.Button(actions,text='Сохранить JSON…',command=self.save).pack(side='left',padx=3)
        ttk.Button(actions,text='Открыть JSON…',command=self.load).pack(side='left',padx=3)
        ttk.Button(actions,text='Проверить',command=self.validate).pack(side='left',padx=3)
        ttk.Label(body,textvariable=self.footer).pack(anchor='w',pady=8)
    def change_flag(self,key,bit,on):
        old=self.vars[key].get()
        self.vars[key].set((old|(1<<bit)) if on else (old&~(1<<bit)))
    def make_colors(self,frame):
        bar=ttk.Frame(frame);bar.pack(anchor='w')
        ttk.Label(bar,text='Банк').pack(side='left')
        for i in range(4):
            ttk.Button(bar,text=str(i+1),width=5,command=lambda j=i:self.set_bank(j)).pack(side='left',padx=3)
        mode=ttk.Frame(frame);mode.pack(anchor='w',pady=9)
        ttk.Radiobutton(mode,text='Off Color',variable=self.color_state,value='inactive',command=self.repaint).pack(side='left')
        ttk.Radiobutton(mode,text='On Color',variable=self.color_state,value='active',command=self.repaint).pack(side='left')
        area=ttk.Frame(frame);area.pack(anchor='w')
        padbox=ttk.LabelFrame(area,text='16 кнопок',padding=8);padbox.pack(side='left',padx=(0,12))
        self.buttons=[]
        for i in range(16):
            b=tk.Button(padbox,width=7,height=3,command=lambda j=i:self.select_pad(j))
            b.grid(row=i//4,column=i%4,padx=3,pady=3)
            self.buttons.append(b)
        palette=ttk.LabelFrame(area,text='Палитра',padding=8);palette.pack(side='left',anchor='n')
        for i,color in enumerate(PALETTE):
            tk.Button(palette,bg=color,width=4,height=2,command=lambda c=color:self.choose_color(c)).grid(row=i//5,column=i%5,padx=2,pady=2)
        self.repaint()
    def set_bank(self,bank):
        self.bank=bank;self.repaint()
    def select_pad(self,pad):
        self.pad=pad;self.repaint()
    def choose_color(self,color):
        getattr(self.profile,self.color_state.get())[self.bank*16+self.pad]=color
        self.repaint()
    def repaint(self):
        colors=getattr(self.profile,self.color_state.get())
        for i,b in enumerate(self.buttons):
            c=colors[self.bank*16+i]
            light=sum(int(c[j:j+2],16) for j in (1,3,5))>380
            b.configure(text=str(i+1)+'\n'+c,bg=c,fg='black' if light else 'white',
                        relief='sunken' if self.pad==i else 'raised')
        self.footer.set(f'Банк {self.bank+1}, кнопка {self.pad+1}. Только локальный профиль.')
    def collect(self):
        for s in SETTINGS:
            self.profile.settings[s.key]=self.vars[s.key].get()
        return self.profile.validate()
    def validate(self):
        try:
            self.collect()
            self.footer.set('Профиль: проверен')
            return True
        except (ValueError,tk.TclError) as e:
            messagebox.showerror('Ошибка проверки',str(e),parent=self.win)
            return False
    def save(self):
        if not self.validate():return
        path=filedialog.asksaveasfilename(parent=self.win,defaultextension='.json',
                    initialfile='MF3D_profile.json',filetypes=[('JSON','*.json')])
        if path:
            try:self.profile.save(path);self.footer.set('Сохранено: '+path)
            except (OSError,ValueError) as e:messagebox.showerror('Ошибка записи',str(e),parent=self.win)
    def load(self):
        path=filedialog.askopenfilename(parent=self.win,filetypes=[('JSON','*.json')])
        if not path:return
        try:
            loaded=Profile.load(path)
            parent=self.win.master
            self.win.destroy()
            ProfileEditor(parent,loaded)
        except (OSError,ValueError,KeyError,TypeError) as e:
            messagebox.showerror('Ошибка чтения',str(e),parent=self.win)
