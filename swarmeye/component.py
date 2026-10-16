from pathlib import Path
import streamlit as st

ASSETS = Path(__file__).parent
_ATLAS = st.components.v2.component(
    'swarmeye_atlas',
    html='<div id="swarmeye-root"></div>',
    css=(ASSETS / 'ui.css').read_text(encoding='utf-8'),
    js=(ASSETS / 'ui.js').read_text(encoding='utf-8'),
    isolate_styles=True,
)


def atlas(data, on_action):
    return _ATLAS(data=data, key='atlas', on_action_change=on_action, width='stretch')
