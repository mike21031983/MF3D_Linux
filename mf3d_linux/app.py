"""Native Linux GUI for MIDI Fighter 3D. Live MIDI only; no EEPROM/DFU SysEx."""
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from . import protocol as p
from .midi_backend import MidiBackend
from .profile_editor import ProfileEditor
from .vendor_sysex import parse_sysex
from .mfs_container import MfsContainer

class App:
    def __init__(self,root):
        self.root=root
        self.root.title('MIDI Fighter 3D — Linux Utility / CP03')
        self.root.minsize(660,570)
        self.midi=MidiBackend()
        self.bank=0
        self.pad=0
        self.note_ch=tk.IntVar(value=p.CHANNEL_NOTES)
        self.aux_ch=tk.IntVar(value=p.CHANNEL_AUX)
        self.vel=tk.IntVar(value=13)
        self.input_name=tk.StringVar()
        self.output_name=tk.StringVar()
        self.status=tk.StringVar(value='USB-MIDI: не подключён')
        self.buttons=[]
        self.build()
        self.refresh()
        self.root.after(70,self.poll)
        root.protocol('WM_DELETE_WINDOW',self.close)
    def build(self):
        host=ttk.Frame(self.root,padding=15)
        host.pack(fill='both',expand=True)
        ttk.Label(host,text='MIDI FIGHTER 3D',font=('Sans',19,'bold')).pack(anchor='w')
        ttk.Label(host,text='Linux Utility / CP01 — управление через документированные MIDI-сообщения. EEPROM и прошивка отключены.',wraplength=620).pack(anchor='w')
        conn=ttk.LabelFrame(host,text='ALSA / RtMidi',padding=8)
        conn.pack(fill='x',pady=7)
        ttk.Label(conn,text='MIDI IN').grid(row=0,column=0)
        self.ins=ttk.Combobox(conn,textvariable=self.input_name,state='readonly')
        self.ins.grid(row=0,column=1,sticky='ew')
        ttk.Label(conn,text='MIDI OUT').grid(row=1,column=0)
        self.outs=ttk.Combobox(conn,textvariable=self.output_name,state='readonly')
        self.outs.grid(row=1,column=1,sticky='ew')
        ttk.Button(conn,text='Обновить',command=self.refresh).grid(row=0,column=2,padx=5)
        ttk.Button(conn,text='Подключить',command=self.connect).grid(row=1,column=2,padx=5)
        conn.columnconfigure(1,weight=1)
        body=ttk.Frame(host)
        body.pack(fill='both',expand=True)
        left=ttk.Frame(body)
        left.pack(side='left',anchor='n')
        banks=ttk.LabelFrame(left,text='Банки',padding=5)
        banks.pack(fill='x')
        for j in range(4):
            ttk.Button(banks,text=str(j+1),width=6,command=lambda n=j:self.bank_select(n)).grid(row=0,column=j,padx=3)
        grid=ttk.LabelFrame(left,text='Пэды / MIDI Note',padding=7)
        grid.pack(pady=6)
        for j in range(16):
            btn=tk.Button(grid,text='',width=7,height=3,relief='raised',
                          command=lambda n=j:self.pad_select(n))
            btn.grid(row=j//4,column=j%4,padx=3,pady=3)
            self.buttons.append(btn)
        right=ttk.LabelFrame(body,text='Подсветка',padding=12)
        right.pack(side='left',fill='both',expand=True,padx=12)
        self.selected=ttk.Label(right,font=('Sans',14,'bold'))
        self.selected.pack(anchor='w')
        ttk.Label(right,text='Color velocity (0–127)').pack(anchor='w',pady=(12,4))
        ttk.Spinbox(right,from_=0,to=127,textvariable=self.vel,width=6).pack(anchor='w')
        ttk.Button(right,text='Применить цвет',command=self.send_color).pack(fill='x',pady=9)
        ttk.Label(right,text='Анимация').pack(anchor='w')
        self.ani=ttk.Combobox(right,state='readonly',values=[
            'Нет','Яркость 0%','Яркость 100%',
            'Gate: 1 beat','Gate: 1/2 beat','Gate: 1/4 beat',
            'Pulse: 1 beat','Pulse: 1/2 beat'])
        self.ani.current(0)
        self.ani.pack(fill='x')
        ttk.Button(right,text='Применить анимацию',command=self.send_animation).pack(fill='x',pady=8)
        ttk.Button(right,text='Снять цветовой override',command=self.clear_color).pack(fill='x')
        ttk.Button(host,text='Редактор настроек и подсветки — локальный профиль (без записи в устройство)',
                   command=lambda:ProfileEditor(self.root)).pack(fill='x',pady=8)
        ttk.Button(host,text='Открыть профиль .mfs — только чтение',command=self.inspect_mfs).pack(fill='x',pady=6)
        ch=ttk.Frame(host)
        ch.pack(fill='x',pady=5)
        ttk.Label(ch,text='Нотный MIDI-канал 0..15:').pack(side='left')
        ttk.Spinbox(ch,from_=0,to=15,textvariable=self.note_ch,width=4).pack(side='left')
        ttk.Label(ch,text='     Вспомогательный:').pack(side='left')
        ttk.Spinbox(ch,from_=0,to=15,textvariable=self.aux_ch,width=4).pack(side='left')
        logbox=ttk.LabelFrame(host,text='MIDI-монитор',padding=5)
        logbox.pack(fill='both',expand=True)
        self.log=tk.Text(logbox,state='disabled',height=5)
        self.log.pack(fill='both',expand=True)
        ttk.Label(host,textvariable=self.status).pack(anchor='w')
        self.repaint()
    def repaint(self):
        for j,button in enumerate(self.buttons):
            button.configure(text=str(j+1)+'\n'+str(p.note_for_pad(self.bank,j)),
                             bg='#37a9c9' if j==self.pad else '#353941',
                             fg='white')
        self.selected.configure(text='Пэд '+str(self.pad+1)+' / Note '+str(p.note_for_pad(self.bank,self.pad)))
    def record(self,line):
        self.log.configure(state='normal')
        self.log.insert('end',line+'\n')
        if int(self.log.index('end-1c').split('.')[0])>110:
            self.log.delete('1.0','15.0')
        self.log.see('end')
        self.log.configure(state='disabled')
    def inspect_mfs(self):
        file=filedialog.askopenfilename(parent=self.root,
            title='Оригинальный профиль MIDI Fighter Utility',
            filetypes=[('MIDI Fighter profile','*.mfs'),('Все файлы','*')])
        if not file:return
        try:description=MfsContainer.from_path(file).describe()
        except (ValueError,OSError) as error:
            messagebox.showerror('Профиль .mfs',str(error),parent=self.root)
            return
        window=tk.Toplevel(self.root)
        window.title('Профиль .mfs — просмотр без изменений')
        window.geometry('690x390')
        view=tk.Text(window,wrap='word')
        view.pack(fill='both',expand=True,padx=12,pady=12)
        view.insert('1.0',description)
        view.configure(state='disabled')

    def refresh(self):
        ins,outs,err=self.midi.available()
        self.ins['values']=ins
        self.outs['values']=outs
        for var,names in ((self.input_name,ins),(self.output_name,outs)):
            if var.get() not in names:
                var.set(next((n for n in names if 'midi fighter' in n.lower()),names[0] if names else ''))
        if err:self.status.set(err)
    def connect(self):
        try:
            self.midi.connect(self.input_name.get(),self.output_name.get())
            self.status.set('Подключено: '+self.midi.input_name)
            self.record('MIDI-порты открыты')
        except Exception as e:
            self.status.set(str(e))
            messagebox.showerror('MIDI',str(e))
    def send(self,cmd):
        try:
            self.midi.send(cmd)
            self.record(f'OUT: {cmd.kind} ch{cmd.channel} note{cmd.note} vel{cmd.velocity}')
        except Exception as e:self.status.set(str(e))
    def bank_select(self,j):
        self.bank=j
        self.repaint()
        if self.midi.output:self.send(p.switch_bank(j,self.aux_ch.get()))
    def pad_select(self,j):
        self.pad=j
        self.repaint()
    def send_color(self):
        try:self.send(p.color(self.bank,self.pad,self.vel.get(),self.note_ch.get()))
        except ValueError as e:self.status.set(str(e))
    def clear_color(self):
        self.send(p.color(self.bank,self.pad,0,self.note_ch.get()))
    def send_animation(self):
        values=[0,18,33,38,39,40,47,48]
        idx=self.ani.current()
        if idx>=0:self.send(p.animation(self.bank,self.pad,values[idx],self.aux_ch.get()))
    def poll(self):
        try:
            for m in self.midi.poll():
                self.record('IN: '+p.describe_incoming(m,self.bank,self.note_ch.get(),self.aux_ch.get()))
                if m.type=='sysex':
                    info=parse_sysex(m)
                    self.record('SYSEx: '+info.category+' / '+str(len(info.data))+' байт')
                    continue
                if m.type=='note_on' and m.channel==self.aux_ch.get() and m.note in range(4) and m.velocity:
                    self.bank=m.note
                    self.repaint()
                elif m.type=='note_on' and m.channel==self.note_ch.get() and m.velocity:
                    idx=p.pad_for_note(self.bank,m.note)
                    if idx is not None:
                        self.pad=idx
                        self.repaint()
        except Exception as e:self.status.set('MIDI poll: '+str(e))
        self.root.after(70,self.poll)
    def close(self):
        self.midi.disconnect()
        self.root.destroy()

def main():
    root=tk.Tk()
    App(root)
    root.mainloop()

if __name__=='__main__':main()
