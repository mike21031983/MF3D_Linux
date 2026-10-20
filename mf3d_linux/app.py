"""Native Linux GUI for MIDI Fighter 3D. Live MIDI only; no EEPROM/DFU SysEx."""
import tkinter as tk
import time
import json
from tkinter import ttk,messagebox,filedialog
from . import protocol as p
from .midi_backend import MidiBackend
from .profile_editor import ProfileEditor
from .vendor_sysex import parse_sysex
from .mfs_container import MfsContainer
from .mfs_backup import backup as mfs_backup, restore as mfs_restore
from .color_read_session import ColorReadSession
from .serializer_capture import PassiveSerializerCapture
from .read_audit import AuditSession
from .device_identity import identity_request
from .config_read import build_main_config_read_request
from .bulk_read import build_bulk_read_request

class App:
    def __init__(self,root):
        self.root=root
        self.root.title('MIDI Fighter 3D — Linux Utility / CP10')
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
        self.read_session=None
        self.last_color_snapshot=None
        self.config_capture=None
        self.config_deadline=None
        self.identity_deadline=None
        self.audit=None
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
        ttk.Button(conn,text='Определить модель (без записи)',command=self.identify).grid(row=2,column=1,sticky='ew',padx=3,pady=3)
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
        ttk.Button(host,text='Считать цвета с MF3D — экспериментальное чтение, без записи',
                   command=self.read_colors).pack(fill='x',pady=4)
        ttk.Button(host,text='Сохранить считанные цвета JSON…',
                   command=self.export_read_colors).pack(fill='x',pady=3)
        configbar=ttk.Frame(host)
        configbar.pack(fill='x',pady=3)
        ttk.Button(configbar,text='Считать основные настройки (только чтение)',
                   command=self.read_main_config).pack(side='left',padx=3)
        ttk.Button(configbar,text='Экспорт наблюдений JSON…',
                   command=self.export_main_config).pack(side='left',padx=3)
        mfsbar=ttk.Frame(host);mfsbar.pack(fill='x',pady=2)
        ttk.Button(mfsbar,text='.mfs → резервный JSON',command=self.backup_mfs).pack(side='left',padx=3)
        ttk.Button(mfsbar,text='Резервный JSON → .mfs (новый файл)',command=self.restore_mfs).pack(side='left',padx=3)
        auditbar=ttk.Frame(host);auditbar.pack(fill='x',pady=4)
        ttk.Button(auditbar,text='Единое чтение: модель + параметры + RGB',
                   command=self.start_audit).pack(side='left',padx=3)
        ttk.Button(auditbar,text='Отчёт JSON…',command=self.export_audit).pack(side='left',padx=3)
        ttk.Button(auditbar,text='Сырая MIDI-трасса…',command=self.export_audit_trace).pack(side='left',padx=3)
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

    def _send_audit_request(self,frame):
        if frame==identity_request():self.midi.request_identity()
        elif frame==build_main_config_read_request():self.midi.send_main_config_read_request()
        elif frame==build_bulk_read_request(1):self.midi.send_color_read_request(1)
        elif frame==build_bulk_read_request(2):self.midi.send_color_read_request(2)
        else:raise ValueError('Disallowed audit command')

    def start_audit(self):
        if self.audit is not None and self.audit.running:
            self.status.set('Комплексное чтение уже выполняется');return
        if (self.identity_deadline is not None or self.config_deadline is not None or
            (self.read_session is not None and self.read_session.state=='reading')):
            self.status.set('Сначала завершите другое чтение');return
        session=AuditSession()
        try:self._send_audit_request(session.begin(time.monotonic()))
        except Exception as error:
            self.status.set('Комплексное чтение не запущено: '+str(error));return
        self.audit=session
        self.last_color_snapshot=None;self.config_capture=None
        self.status.set('Комплексное чтение: идентификация, без записи')

    def export_audit(self):
        if self.audit is None or self.audit.running or self.audit.phase=='idle':
            self.status.set('Нет завершённого диагностического сеанса');return
        path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',
            initialfile='MF3D_read_audit.json',filetypes=[('JSON','*.json')])
        if not path:return
        try:self.audit.save_report(path)
        except (OSError,ValueError,RuntimeError) as error:
            messagebox.showerror('Отчёт MF3D',str(error),parent=self.root)
        else:self.status.set('Отчёт сохранён в новый JSON без серийного номера')

    def export_audit_trace(self):
        if self.audit is None or self.audit.phase=='idle':
            self.status.set('Нет диагностического сеанса');return
        if not messagebox.askyesno('Приватность SysEx',
            'Сырые сообщения могут содержать уникальный идентификатор устройства. '
            'Сохранить локально? Не публикуйте файл в GitHub.',parent=self.root):
            return
        path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',
            initialfile='MF3D_PRIVATE_MIDI_trace.json',filetypes=[('JSON','*.json')])
        if not path:return
        try:self.audit.save_trace(path)
        except (OSError,ValueError,RuntimeError) as error:
            messagebox.showerror('Трасса MF3D',str(error),parent=self.root)
        else:self.status.set('Приватная MIDI-трасса сохранена локально')

    def identify(self):
        if self.audit is not None and self.audit.running:
            self.status.set('Сначала завершите комплексное чтение');return
        if self.identity_deadline is not None:
            self.status.set('Идентификация уже выполняется');return
        try:self.midi.request_identity()
        except Exception as e:
            self.status.set('Идентификация не запущена: '+str(e));return
        self.identity_deadline=time.monotonic()+3.0
        self.read_session=None
        self.config_capture=None
        self.config_deadline=None
        self.last_color_snapshot=None
        self.status.set('Запрос модели 05 отправлен, ожидается 05 01')

    def read_colors(self):
        if self.audit is not None and self.audit.running:
            self.status.set('Сначала завершите комплексное чтение');return
        if self.read_session is not None and self.read_session.state=='reading':
            self.status.set('Чтение уже выполняется');return
        session=ColorReadSession()
        try:
            session.begin(time.monotonic())
            self.midi.send_color_read_request(1)
        except Exception as ex:
            self.status.set('Чтение не запущено: '+str(ex));return
        self.read_session=session;self.last_color_snapshot=None
        self.status.set('Чтение RGB-блока 1, без записи в устройство')

    def export_read_colors(self):
        if self.last_color_snapshot is None:
            self.status.set('Нужны два полностью считанных блока');return
        path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',
            initialfile='MF3D_read_colors.json',filetypes=[('JSON','*.json')])
        if not path:return
        doc={'format':'MF3D_READ_COLORS_V1','device':'MIDI Fighter 3D',
             'note':'Only LED buffers; NOT persistent device settings',
             'inactive_rgb7':list(self.last_color_snapshot[1]),
             'active_rgb7':list(self.last_color_snapshot[2])}
        try:
            with open(path,'w',encoding='utf-8') as stream:
                json.dump(doc,stream,indent=2,ensure_ascii=False)
            self.status.set('Сохранены только цвета: '+path)
        except OSError as ex:self.status.set('Ошибка сохранения: '+str(ex))

    def read_main_config(self):
        if self.audit is not None and self.audit.running:
            self.status.set('Сначала завершите комплексное чтение');return
        if self.config_deadline is not None:
            self.status.set('Чтение уже выполняется')
            return
        capture=PassiveSerializerCapture()
        try:
            self.midi.send_main_config_read_request()
        except Exception as e:
            self.status.set('Чтение не запущено: '+str(e))
            return
        self.config_capture=capture
        self.config_deadline=time.monotonic()+4.0
        self.status.set('Запрошен ответ 02 01. В память ничего не записывается')

    def export_main_config(self):
        if self.config_capture is None or not self.config_capture.frames:
            self.status.set('Нет принятых ответов 02 01')
            return
        path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',
            initialfile='MF3D_partial_settings.json',filetypes=[('JSON','*.json')])
        if not path:return
        try:
            self.config_capture.save_json(path)
            self.status.set('Сохранены НЕПОЛНЫЕ наблюдения: '+path)
        except OSError as e:
            self.status.set('Ошибка экспорта: '+str(e))

    def backup_mfs(self):
        src=filedialog.askopenfilename(parent=self.root,title='Оригинальный профиль MIDI Fighter',
                filetypes=[('MIDI Fighter profile','*.mfs'),('Все файлы','*')])
        if not src:return
        dst=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',
                initialfile='MF3D_MFS_backup.json',filetypes=[('JSON','*.json')])
        if not dst:return
        try:
            mfs_backup(src,dst)  # exclusive-create, cannot overwrite
            self.status.set('Создана точная резервная копия .mfs')
        except (OSError,ValueError) as exc:
            messagebox.showerror('Копирование .mfs',str(exc),parent=self.root)

    def restore_mfs(self):
        src=filedialog.askopenfilename(parent=self.root,title='Резервный JSON',
                filetypes=[('JSON','*.json')])
        if not src:return
        dst=filedialog.asksaveasfilename(parent=self.root,defaultextension='.mfs',
                initialfile='MF3D_restored.mfs',filetypes=[('MIDI Fighter profile','*.mfs')])
        if not dst:return
        try:
            mfs_restore(src,dst)
            self.status.set('Профиль .mfs восстановлен побайтно в новый файл')
        except (OSError,ValueError) as exc:
            messagebox.showerror('Восстановление .mfs',str(exc),parent=self.root)

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
            self.identity_deadline=None
            self.audit=None
            self.read_session=None
            self.config_capture=None
            self.config_deadline=None
            self.last_color_snapshot=None
            self.status.set('Подключено: '+self.midi.input_name+'; требуется определение модели')
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
                    if self.audit is not None and self.audit.running:
                        try:
                            if self.audit.phase=='identity':self.midi.observe_identity(m)
                            query=self.audit.feed(m,time.monotonic())
                            if query is not None:self._send_audit_request(query)
                            if self.audit.phase=='finished':
                                self.status.set('Считаны RGB; полнота основных настроек НЕ доказана')
                            elif self.audit.phase=='failed':
                                self.midi.expire_identity()
                                self.status.set('Комплексное чтение остановлено: '+str(self.audit.error))
                        except Exception as error:
                            self.audit.fail(str(error))
                            self.midi.expire_identity()
                            self.status.set('Ошибка комплексного чтения: '+str(error))
                        continue
                    if self.identity_deadline is not None:
                        try: ident=self.midi.observe_identity(m)
                        except ValueError as e:
                            self.midi.expire_identity()
                            self.identity_deadline=None
                            self.status.set('Ошибка ответа модели: '+str(e))
                            ident=None
                        if ident is not None:
                            self.identity_deadline=None
                            if ident.is_standard_mf3d:
                                self.status.set('Подтверждён MF3D '+ident.family_code+':'+ident.model_number)
                            else:
                                self.status.set('Другая модель '+ident.family_code+':'+ident.model_number+'; чтение заблокировано')
                    info=parse_sysex(m)
                    self.record('SYSEx: '+info.category+' / '+str(len(info.data))+' байт')
                    if self.config_deadline is not None and self.config_capture is not None:
                        try:
                            if self.config_capture.feed(m):
                                self.status.set('Получено '+str(len(self.config_capture.values))+
                                    ' параметров последнего ответа; полнота не подтверждена')
                        except ValueError as ex:
                            self.config_deadline=None
                            self.status.set('Некорректный ответ 02 01: '+str(ex))
                    if self.read_session is not None and self.read_session.state=='reading':
                        try:
                            next_request=self.read_session.feed(m,time.monotonic())
                            if next_request is not None:
                                self.midi.send_color_read_request(2)
                                self.status.set('Блок 1 считан; запрошен блок 2')
                            elif self.read_session.state=='complete':
                                self.last_color_snapshot=self.read_session.snapshot()
                                self.status.set('Считаны оба RGB-блока: 192+192 значения')
                        except Exception as ex:
                            self.read_session.fail(str(ex))
                            self.status.set('Чтение остановлено: '+str(ex))
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
        if self.audit is not None and self.audit.running:
            try:
                query=self.audit.tick(time.monotonic())
                if query is not None:self._send_audit_request(query)
                if self.audit.phase=='failed':
                    self.midi.expire_identity()
                    self.status.set('Комплексное чтение остановлено: '+str(self.audit.error))
            except Exception as error:
                self.audit.fail(str(error));self.midi.expire_identity()
                self.status.set('Ошибка комплексного чтения: '+str(error))
        if self.identity_deadline is not None and time.monotonic()>=self.identity_deadline:
            self.identity_deadline=None
            self.midi.expire_identity()
            self.status.set('Тайм-аут 05 01: модель не подтверждена, чтение запрещено')
        if self.config_deadline is not None and time.monotonic()>=self.config_deadline:
            self.config_deadline=None
            if self.config_capture is not None and self.config_capture.frames:
                self.status.set('Основные параметры: '+str(len(self.config_capture.values))+
                    ' параметров последнего ответа, ПОЛНОТА НЕ ПОДТВЕРЖДЕНА')
            else:
                self.status.set('Тайм-аут ответа 02 01; настройки не получены')
        if self.read_session is not None and self.read_session.expire(time.monotonic()):
            self.status.set('Тайм-аут чтения цветов; неполные данные отброшены')
        self.root.after(70,self.poll)
    def close(self):
        self.midi.disconnect()
        self.root.destroy()

def main():
    root=tk.Tk()
    App(root)
    root.mainloop()

if __name__=='__main__':main()
