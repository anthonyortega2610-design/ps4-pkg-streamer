import json
import os
import queue
import threading
import time
from ftplib import FTP, error_perm
from urllib.parse import urlsplit, unquote
from urllib.request import Request, urlopen
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

class Cancelled(Exception):
    pass

class Reader:
    def __init__(self, q, stop):
        self.q, self.stop = q, stop
    def read(self, size):
        while not self.stop.is_set():
            try:
                item = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            if isinstance(item, Exception):
                raise item
            return item
        raise Cancelled('Transfer canceled')

class Streamer(App):
    title = 'PS4 PKG Streamer'
    def build(self):
        Window.clearcolor = (0.055, 0.07, 0.11, 1)
        self.stop = threading.Event()
        self.busy = False
        self.events = queue.Queue()
        self.settings_file = os.path.join(self.user_data_dir, 'settings.json')
        try:
            with open(self.settings_file) as f:
                saved = json.load(f)
        except (OSError, ValueError):
            saved = {}
        scroll = ScrollView()
        root = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10), size_hint_y=None)
        root.bind(minimum_height=root.setter('height'))
        scroll.add_widget(root)
        root.add_widget(Label(text='PS4 PKG Streamer', font_size='26sp', bold=True, size_hint_y=None, height=dp(55)))
        root.add_widget(Label(text='Direct URL → phone → PS4', size_hint_y=None, height=dp(30), color=(0.65,0.73,0.9,1)))
        self.fields = {}
        for key, caption, default in [('ip','PS4 local IP',''),('port','FTP port','2121'),('folder','PS4 folder','/data/pkg'),('url','Direct HTTP(S) package URL',''),('filename','Filename (blank = detect from URL)','')]:
            root.add_widget(Label(text=caption, size_hint_y=None, height=dp(25), halign='left'))
            field = TextInput(text=saved.get(key, default) if key in ('ip','port','folder') else '', multiline=False, size_hint_y=None, height=dp(48), background_color=(0.14,0.18,0.26,1), foreground_color=(1,1,1,1), cursor_color=(0.5,0.7,1,1), padding=[dp(10),dp(12)])
            self.fields[key] = field
            root.add_widget(field)
        self.bar = ProgressBar(max=100, size_hint_y=None, height=dp(24))
        root.add_widget(self.bar)
        self.status = Label(text='Ready. Enable GoldHEN FTP first.', size_hint_y=None, height=dp(80), font_size='14sp')
        self.status.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        root.add_widget(self.status)
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        self.start_button = Button(text='Start transfer', background_normal='', background_color=(0.25,0.40,0.95,1))
        self.start_button.bind(on_release=self.prepare)
        self.cancel_button = Button(text='Cancel', disabled=True)
        self.cancel_button.bind(on_release=lambda *_: self.cancel())
        row.add_widget(self.start_button); row.add_widget(self.cancel_button)
        root.add_widget(row)
        note = Label(text='Keep this app visible and your phone awake.\nUse a trusted home Wi-Fi network. FTP is unencrypted.\nOnly transfer files you are authorized to download.', size_hint_y=None, height=dp(90), font_size='12sp', color=(0.65,0.73,0.9,1))
        note.bind(size=lambda w,s: setattr(w,'text_size',(s[0],None)))
        root.add_widget(note)
        Clock.schedule_interval(self.poll, 0.15)
        return scroll

    def prepare(self, *_):
        if self.busy: return
        v = {k:w.text.strip() for k,w in self.fields.items()}
        try:
            if not v['ip']: raise ValueError('Enter the PS4 local IP.')
            v['port'] = int(v['port'])
            if not 1 <= v['port'] <= 65535: raise ValueError('Invalid FTP port.')
            parsed = urlsplit(v['url'])
            if parsed.scheme not in ('http','https') or not parsed.netloc: raise ValueError('Enter a full HTTP(S) URL.')
            if not v['folder'].startswith('/') or any(c in v['folder'] for c in ('\r','\n','\0')): raise ValueError('Use an absolute PS4 folder path.')
            if any(p in ('.','..') for p in v['folder'].split('/')): raise ValueError('Folder cannot contain . or .. components.')
            name = v['filename'] or unquote(parsed.path.rsplit('/',1)[-1]) or 'download.pkg'
            if any(c in name for c in ('/','\\','\r','\n','\0')): raise ValueError('Use a filename without a path.')
            if not name.lower().endswith('.pkg'): name += '.pkg'
            v['filename'] = name
        except (ValueError, TypeError) as e:
            self.status.text = str(e); return
        panel = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(12))
        text = Label(text='Send to PS4?\nAn existing file with this name will be replaced.\nAn existing .part file will restart from zero.', text_size=(dp(260),None))
        panel.add_widget(text)
        buttons = BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(10))
        yes = Button(text='Start'); no = Button(text='Back')
        buttons.add_widget(no); buttons.add_widget(yes); panel.add_widget(buttons)
        popup = Popup(title='Confirm transfer', content=panel, size_hint=(0.92,None), height=dp(300))
        no.bind(on_release=lambda *_: popup.dismiss())
        def begin(*_):
            popup.dismiss(); self.begin(v)
        yes.bind(on_release=begin); popup.open()

    def begin(self, v):
        try:
            with open(self.settings_file,'w') as f:
                json.dump({k:str(v[k]) for k in ('ip','port','folder')},f)
        except OSError: pass
        self.busy = True; self.stop.clear(); self.bar.value=0
        self.start_button.disabled=True; self.cancel_button.disabled=False
        self.status.text='Connecting…'
        threading.Thread(target=self.transfer,args=(v,),daemon=True).start()

    def cancel(self):
        self.stop.set(); self.cancel_button.disabled=True
        self.status.text='Cancel requested. Waiting for network operation…'

    def poll(self, _):
        for _ in range(30):
            try: kind, data = self.events.get_nowait()
            except queue.Empty: break
            if kind == 'progress':
                pct,text=data
                self.bar.value=pct; self.status.text=text
            elif kind == 'status': self.status.text=data
            elif kind == 'done':
                self.busy=False; self.start_button.disabled=False; self.cancel_button.disabled=True
                ok,text=data; self.status.text=text
                if ok: self.bar.value=100

    def transfer(self,v):
        ftp=None; response=None; producer=None
        q=queue.Queue(maxsize=16)
        finished=threading.Event()
        total=None; sent=0
        def put(item):
            while not self.stop.is_set() and not finished.is_set():
                try: q.put(item,timeout=0.2); return
                except queue.Full: pass
        def produce():
            try:
                while not self.stop.is_set() and not finished.is_set():
                    block=response.read(256*1024)
                    put(block)
                    if not block: return
            except Exception as e: put(e)
        try:
            response=urlopen(Request(v['url'],headers={'User-Agent':'PS4-PKG-Streamer/0.1','Accept-Encoding':'identity'}),timeout=30)
            if 'text/html' in response.headers.get('Content-Type','').lower(): raise ValueError('URL returned a webpage, not a package.')
            raw=response.headers.get('Content-Length','')
            total=int(raw) if raw.isdigit() else None
            ftp=FTP(); ftp.connect(v['ip'],v['port'],timeout=30); ftp.login()
            ftp.cwd('/')
            for part in filter(None,v['folder'].split('/')):
                try: ftp.cwd(part)
                except error_perm:
                    ftp.mkd(part); ftp.cwd(part)
            if self.stop.is_set(): raise Cancelled()
            producer=threading.Thread(target=produce,daemon=True); producer.start()
            started=time.monotonic(); last=0
            def progress(block):
                nonlocal sent,last
                if self.stop.is_set(): raise Cancelled()
                sent+=len(block); now=time.monotonic()
                if now-last<0.4: return
                speed=sent/max(now-started,0.01)
                pct=100*sent/total if total else 0
                text=f'{sent/1e9:.2f} GB • {speed/1e6:.2f} MB/s'
                if total: text+=f'\n{pct:.1f}% • {max(total-sent,0)/max(speed,1)/60:.1f} min left'
                else: text+='\nTotal size not supplied by server'
                self.events.put(('progress',(min(pct,99.9),text))); last=now
            temp=v['filename']+'.part'
            ftp.storbinary('STOR '+temp,Reader(q,self.stop),blocksize=256*1024,callback=progress)
            if self.stop.is_set(): raise Cancelled()
            if total is not None and sent!=total: raise ValueError('Size mismatch. Partial file was not finalized.')
            try: ftp.delete(v['filename'])
            except error_perm: pass
            ftp.rename(temp,v['filename'])
            self.events.put(('done',(True,'Finished! Saved in '+v['folder']+'/'+v['filename'])))
        except Cancelled:
            self.events.put(('done',(False,'Canceled. A .part file may remain on the PS4.')))
        except Exception as e:
            # Avoid displaying signed URLs or tokens in error messages.
            self.events.put(('done',(False,type(e).__name__+': Transfer failed. Check URL, FTP, storage and Wi-Fi. A .part file may remain.')))
        finally:
            finished.set()
            if response:
                try: response.close()
                except Exception: pass
            if ftp:
                try: ftp.close()
                except Exception: pass

    def on_pause(self):
        return True

    def on_stop(self):
        self.stop.set()

if __name__ == '__main__':
    Streamer().run()
