"""Privacy-checked immutable preview fixture boundary."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any
from .preview_limits import WorkflowPreviewLimits

_SENSITIVE=("token","secret","password","credential","claim","authorization","cookie","path","stack","exception","raw","code","script","sql","command","url","content","bytes")

def normalize_preview_sample(value: Any, limits: WorkflowPreviewLimits)->Any:
    count=[0]
    def walk(item:Any,depth:int)->Any:
        if depth>limits.max_nested_depth: raise ValueError("fixture nesting exceeds preview limits")
        if item is None or isinstance(item,(bool,int,float)):
            count[0]+=1; return item
        if isinstance(item,str):
            if len(item)>limits.max_string_length: raise ValueError("fixture string exceeds preview limits")
            count[0]+=1; return item
        if callable(item) or isinstance(item,(bytes,bytearray,memoryview)): raise ValueError("fixture contains unsupported value")
        if isinstance(item,Mapping):
            if len(item)>limits.max_input_collection_size: raise ValueError("fixture mapping exceeds preview limits")
            output={}
            for key in sorted(item):
                if not isinstance(key,str) or not key or len(key)>64: raise ValueError("fixture key invalid")
                normalized=key.lower().replace("-","_")
                if any(part in normalized for part in _SENSITIVE): raise ValueError("fixture key is protected")
                count[0]+=1; output[key]=walk(item[key],depth+1)
            if count[0]>limits.max_output_fields*limits.max_input_collection_size: raise ValueError("fixture field count exceeds preview limits")
            return MappingProxyType(output)
        if isinstance(item,Sequence) and not isinstance(item,(str,bytes,bytearray)):
            if len(item)>limits.max_input_collection_size: raise ValueError("fixture collection exceeds preview limits")
            return tuple(walk(x,depth+1) for x in item)
        raise ValueError("fixture contains unsupported value")
    return walk(value,1)

class InMemoryWorkflowPreviewFixtureProvider:
    def __init__(self, fixtures:Mapping[str,Any]|None=None): self._fixtures=dict(fixtures or {})
    def get_fixture(self,tenant_id:str,fixture_id:str)->Any|None:
        return self._fixtures.get(f"{tenant_id}:{fixture_id}")
