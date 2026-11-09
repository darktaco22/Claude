"""CASH 4 GOLD (a Meme Royale commercial): the dialogue. (id, speaker, text). Kokoro voices.
pitch < 1 lowers the voice (resample), for the smoker and the sleepy sloth."""
VOICE = {'broker': ('af_jessica', 0.9, 0.9), 'groom': ('am_eric', 1.05, 1.0), 'grandma': ('bf_emma', 0.85, 1.04),
         'slerf': ('am_michael', 0.72, 0.85)}
LINES = [
    ('g_ring',   'groom',   "How much for the ring? The wedding's in twenty minutes."),
    ('b_forty',  'broker',  "Forty bucks."),
    ('g_perfect','groom',   "Perfect. That's a full position."),
    ('m_harold', 'grandma', "This is Harold. He'd want me to buy the dip."),
    ('b_ashes',  'broker',  "Ashes are thirty a pound."),
    ('m_big',    'grandma', "He was a big man."),
    ('b_useless','broker',  "He's not gold. He's useless."),
    ('b_line',   'broker',  "That one's been in line since the last bull run."),
    ('b_free',   'broker',  "You want to lose everything? Lose it here. It's free."),
    ('g_rugged', 'groom',   "I just rugged a guy... and I still have my ring!"),
    ('m_look',   'grandma', "Harold, look!"),
    ('s_wen',    'slerf',   "...wen launch?"),
]
