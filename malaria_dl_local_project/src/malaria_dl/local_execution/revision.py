"""Explicit cross-platform technical identity, never numeric equivalence."""
import re


def valid_environment(env):
    return (isinstance(env,dict) and env.get('execution_mode')=='local_python'
            and env.get('platform')=='Darwin' and env.get('machine')=='arm64'
            and env.get('device')=='CPU' and env.get('precision')=='float32'
            and isinstance(env.get('packages'),dict) and bool(env['packages'])
            and isinstance(env.get('determinism_environment'),dict)
            and bool(re.fullmatch(r'[a-f0-9]{64}',str(env.get('source_sha256',''))))
            and isinstance(env.get('python'),str) and isinstance(env.get('tensorflow'),str))
