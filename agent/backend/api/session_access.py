"""Capability-bound debug sessions. Production user identity still belongs to the gateway."""
import secrets
from threading import RLock
from fastapi import HTTPException

class SessionAccess:
    def __init__(self):
        self._sessions={}
        self._lock=RLock()

    def chat(self,session_id,user_id,token,existing_trace=False):
        if not session_id.strip() or not user_id.strip():raise HTTPException(422,'会话和用户标识不能为空')
        with self._lock:
            if session_id not in self._sessions:
                if existing_trace:
                    raise HTTPException(403,'该会话已有执行记录，请创建新会话')
                self._sessions[session_id]=(user_id,secrets.token_urlsafe(32))
            else:
                self.require(session_id,user_id,token)
            return self._sessions[session_id][1]

    def require(self,session_id,user_id,token):
        with self._lock:
            entry=self._sessions.get(session_id)
            if not entry or entry[0]!=user_id or not token or not secrets.compare_digest(entry[1],token):
                raise HTTPException(403,'无权访问该会话，请使用当前用户的新会话')

session_access=SessionAccess()
