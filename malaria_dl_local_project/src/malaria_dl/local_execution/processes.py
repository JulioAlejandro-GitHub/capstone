"""PID identities and loss-of-contact semantics, valid on Darwin and Linux."""
import os
import platform
import time
import psutil
HEARTBEAT_SECONDS=15
HEARTBEAT_EXPIRY_SECONDS=60


def identity(pid):
    p=psutil.Process(pid)
    return {'pid':pid,'created_at':p.create_time(),'host':platform.node(),'platform':platform.system()}


def still_alive(proof):
    if proof['host']!=platform.node() or proof['platform']!=platform.system():
        raise ValueError('PROCESS_HOST_UNPROVEN')
    try:return psutil.Process(proof['pid']).create_time()==proof['created_at']
    except psutil.NoSuchProcess:return False


class ProcessTracker:
    def __init__(self,pid):self.parent=identity(pid);self.children={};self.uncertain=False
    def sample(self):
        if not still_alive(self.parent):return
        try:
            for p in psutil.Process(self.parent['pid']).children(recursive=True):
                self.children[(p.pid,p.create_time())]=identity(p.pid)
        except (psutil.NoSuchProcess,psutil.AccessDenied):self.uncertain=True
    def exit_proof(self,exit_code):
        alive=[p for p in [self.parent,*self.children.values()] if still_alive(p)]
        return {'parent':self.parent,'children':list(self.children.values()),'exit_code':exit_code,
                'remaining':alive,'absence_proven':not alive and not self.uncertain,
                'scope':'observed descendants only; escaped unobserved children not accredited'}


def heartbeat_status(last_seen,now=None):
    return 'uncertain' if (time.time() if now is None else now)-last_seen>HEARTBEAT_EXPIRY_SECONDS else 'connected'
