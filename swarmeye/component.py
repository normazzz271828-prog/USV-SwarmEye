from pathlib import Path
from functools import lru_cache
import streamlit as st

ASSETS = Path(__file__).parent
@lru_cache(maxsize=2)
def renderer(css, js):
    return st.components.v2.component(
        'swarmeye_atlas',
        html='<div id="swarmeye-root"></div>',
        css=css, js=js, isolate_styles=True,
    )


def atlas(data, on_action):
    # Cloud can reload Python while retaining imported modules. Key the renderer
    # by asset contents so CSS/JS releases do not require a manual service restart.
    mount = renderer((ASSETS / 'ui.css').read_text(encoding='utf-8'),
                     (ASSETS / 'ui.js').read_text(encoding='utf-8'))
    return mount(data=data, key='atlas', on_action_change=on_action, width='stretch')
