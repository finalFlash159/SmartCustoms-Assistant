from fastapi import Request, Depends
from py_vncorenlp import VnCoreNLP
from typing import Callable

def get_vncorenlp(request: Request) -> VnCoreNLP:
    return request.app.state.vncorenlp

def get_segmenter(vncorenlp: VnCoreNLP = Depends(get_vncorenlp)) -> Callable[[str], str]:
    def segmenter(text: str) -> str:
        return " ".join(vncorenlp.word_segment(text))
    return segmenter

def get_cross_reranker(request: Request):
    return request.app.state.cross_reranker
