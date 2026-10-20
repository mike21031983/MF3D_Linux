"""Nonblocking two-block read-only MF3D color capture. Never connects/sends automatically."""
from dataclasses import dataclass,field
from .bulk_read import ColorBulkCapture,build_bulk_read_request
@dataclass
class ColorReadSession:
    state:str='idle'
    active:ColorBulkCapture|None=None
    results:dict=field(default_factory=dict)
    deadline:float|None=None
    timeout_seconds:float=4.0
    error:str|None=None
    def begin(self,now:float)->bytes:
        if self.state!='idle':raise RuntimeError('Already started')
        self.state='reading';self.active=ColorBulkCapture(1)
        self.deadline=now+self.timeout_seconds
        return build_bulk_read_request(1)
    def feed(self,message,now:float)->bytes|None:
        if self.state!='reading':return None
        if now>=self.deadline:
            self.fail('Read timeout');raise TimeoutError(self.error)
        try:consumed=self.active.feed(message)
        except (ValueError,RuntimeError) as e:
            self.fail('Malformed response: '+str(e));raise
        if not consumed or not self.active.complete:return None
        self.results[self.active.tag]=self.active.get_values()
        if self.active.tag==1:
            self.active=ColorBulkCapture(2)
            self.deadline=now+self.timeout_seconds
            return build_bulk_read_request(2)
        if set(self.results)!={1,2}:
            self.fail('Missing color buffer');raise ValueError(self.error)
        self.active=None;self.deadline=None;self.state='complete'
        return None
    def expire(self,now:float)->bool:
        if self.state=='reading' and now>=self.deadline:
            self.fail('Read timeout');return True
        return False
    def fail(self,reason:str):
        self.state='failed';self.error=reason;self.results.clear()
        self.active=None;self.deadline=None
    def snapshot(self):
        if self.state!='complete' or set(self.results)!={1,2}:
            raise RuntimeError('Complete two-buffer read required')
        return dict(self.results)
