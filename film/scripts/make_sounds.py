"""Generates every sound for the films in code: no stock audio.

Run from the my-film folder:  python3 scripts/make_sounds.py
Writes public/sfx/*.wav (sound effects) and public/sfx/boot_score.wav (music for BOOT.).
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'sfx')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def save(name, x, peak=0.9):
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x)) or 1.0
    x = x / m * peak
    data = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print('wrote', name, f'{len(x) / SR:.2f}s')


def secs(d):
    return np.arange(int(d * SR)) / SR


def smooth(x, k):
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, mode='same')


def highpass(x, k):
    return x - smooth(x, k)


def fft_convolve(a, b):
    n = len(a) + len(b) - 1
    size = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(a, size) * np.fft.rfft(b, size), size)[:n]


def reverb(x, length=2.2, decay=0.55, mix=0.25):
    t = secs(length)
    ir = rng.standard_normal(len(t)) * np.exp(-t / decay)
    ir = smooth(ir, 6)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = fft_convolve(x, ir)[: len(x)]
    return x * (1 - mix) + wet * mix


def add(buf, sig, t0, vol=1.0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * vol


def fades(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na > 0:
        e[:na] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, min(na, n)))[: min(na, n)]
    if nr > 0 and nr < n:
        e[-nr:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, nr))
    return e


# ---------------- instruments ----------------

def pad(freqs, dur, attack=2.0, release=2.0, bright=0.3):
    t = secs(dur)
    s = np.zeros_like(t)
    for f in freqs:
        for d in (-0.0025, 0.0025):
            ph = rng.uniform(0, 6.28)
            vib = 0.6 * np.sin(2 * np.pi * 0.17 * t + ph)
            s += np.sin(2 * np.pi * f * (1 + d) * t + vib + ph)
            s += bright * 0.5 * np.sin(2 * np.pi * 2 * f * (1 + d) * t + ph)
            s += bright * 0.25 * np.sin(2 * np.pi * 3 * f * (1 + d) * t + ph)
    s *= 1 + 0.12 * np.sin(2 * np.pi * 0.11 * t)
    return s / (len(freqs) * 2) * fades(len(t), attack, release)


def pluck(f, dur=1.4):
    t = secs(dur)
    s = sum(np.sin(2 * np.pi * f * n * t) * np.exp(-t * (2.5 + n * 1.8)) / n ** 1.3 for n in range(1, 7))
    return s * fades(len(t), 0.003, 0.05)


def bell(f, dur=2.5):
    t = secs(dur)
    parts = [(1, 1, 1.2), (2.76, 0.5, 2.5), (5.4, 0.25, 4), (8.93, 0.12, 6)]
    s = sum(a * np.sin(2 * np.pi * f * p * t) * np.exp(-t * d) for p, a, d in parts)
    return s * fades(len(t), 0.002, 0.1)


def kick(dur=0.45, f0=110, f1=42, tau=0.16):
    t = secs(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau)


def hat(dur=0.08, tau=0.025):
    t = secs(dur)
    return highpass(rng.standard_normal(len(t)), 3) * np.exp(-t / tau)


def bass(f, dur):
    t = secs(dur)
    s = sum(np.sin(2 * np.pi * f * n * t) * np.exp(-t * n * 2.2) / n for n in range(1, 6))
    return s * fades(len(t), 0.005, 0.05) * np.exp(-t * 1.5)


def riser(dur, f0=180, f1=900):
    t = secs(dur)
    u = t / dur
    f = f0 * (f1 / f0) ** u
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    noise = highpass(rng.standard_normal(len(t)), 4) * (u ** 2)
    return (tone * 0.5 + noise * 0.4) * (u ** 1.6)


# ---------------- music for BOOT. ----------------
A1, D2, E2, F2, G2 = 55.0, 73.42, 82.41, 87.31, 98.0
A2, B2, C3, Cs3, D3, E3, F3, Fs3, G3, Gs3 = 110.0, 123.47, 130.81, 138.59, 146.83, 164.81, 174.61, 185.0, 196.0, 207.65
A3, C4, Cs4, D4, E4 = 220.0, 261.63, 277.18, 293.66, 329.63
A4, Bb4, C5, Cs5, E5, A5 = 440.0, 466.16, 523.25, 554.37, 659.25, 880.0

TOTAL = 3960 / 30
score = np.zeros(int((TOTAL + 1) * SR))
F = lambda frame: frame / 30.0  # noqa: E731
BEAT = 0.5  # 120 bpm: one beat = 15 frames, montage cuts land every 2 beats

# 1. Intro: soft hopeful A minor, cut dead at the triple fault
add(score, pad([A2, E3, C4], F(310), attack=3, release=0.06), 0, 0.5)
for i, n in enumerate([E4, C4, A3, C4]):
    add(score, pluck(n, 2.0), 1.5 + i * 2.0, 0.18)

# 2. Shadow appears: low drone + dissonant shimmer
add(score, pad([A1, D2], 7.8, attack=2.5, release=1.2, bright=0.5), F(350), 0.75)
add(score, pad([A4, Bb4], 6.0, attack=3, release=1.5, bright=0), F(400), 0.12)

# 3. Glasses: gentle hope with bells
add(score, pad([A2, E3, C4, E4], 5.6, attack=1.5, release=1.5), F(565), 0.38)
for i, n in enumerate([E5, C5, A4]):
    add(score, bell(n), F(590) + i * 1.4, 0.16)

# 4. Montage + grind: driving pulse, Am F C G
prog = [(A2, [A2, E3, C4]), (F2 * 2, [F3, A3, C4]), (C3, [C3, G3, E4]), (G2 * 2, [G3, B2 * 2, D4])]


def pulse_section(t0, t1, vol=1.0, hats16=False, chords=prog, lead=None):
    beats = int((t1 - t0) / BEAT)
    for b in range(beats):
        t = t0 + b * BEAT
        add(score, kick(), t, 0.55 * vol)
        add(score, hat(), t + BEAT / 2, 0.12 * vol)
        if hats16:
            add(score, hat(0.05, 0.015), t + BEAT / 4, 0.07 * vol)
            add(score, hat(0.05, 0.015), t + 3 * BEAT / 4, 0.07 * vol)
        root, chord = chords[(b // 4) % len(chords)]
        add(score, bass(root / 2 if root > 100 else root, BEAT / 2), t, 0.35 * vol)
        add(score, bass(root / 2 if root > 100 else root, BEAT / 2), t + BEAT / 2, 0.25 * vol)
        if b % 4 == 0:
            add(score, pad(chord, BEAT * 4 + 0.3, attack=0.2, release=0.4), t, 0.3 * vol)
        if lead is not None:
            add(score, pluck(lead[(b * 2) % len(lead)] * 2, 0.5), t, 0.12 * vol)
            add(score, pluck(lead[(b * 2 + 1) % len(lead)] * 2, 0.5), t + BEAT / 2, 0.1 * vol)


pulse_section(F(720), F(1260), vol=0.85)
pulse_section(F(1260), F(1545), vol=1.0, hats16=True, lead=[A3, C4, E4, C4])

# 5. Kernel panic: silence + ringing ears
t = secs(4)
add(score, np.sin(2 * np.pi * 3100 * t) * np.exp(-t / 1.4) * fades(len(t), 0.01, 0.5), F(1548), 0.05)

# 6. Rock bottom: low, sad
add(score, pad([A1, E2, C3], 8.6, attack=3, release=2, bright=0.2), F(1640), 0.6)

# 7. The LED: almost silent, a small hopeful motif
for i, n in enumerate([A4, C5, E5]):
    add(score, pluck(n, 2.2), F(1905) + i * 1.5, 0.16)
add(score, pad([A2, E3], 6.5, attack=2, release=1.5, bright=0), F(1890), 0.18)

# 8. Stand up: swell into him rising, then a determined low hit
add(score, riser(F(2134) - F(2075), 90, 420), F(2075), 0.25)
add(score, kick(1.4, 90, 32, 0.5), F(2134), 0.8)
add(score, pad([A1, A2, E3], 3.2, attack=0.02, release=1.5, bright=0.5), F(2134), 0.5)

# 9. The run: drive builds, lead arpeggio from Run B
pulse_section(F(2220), F(2490), vol=0.95)
pulse_section(F(2490), F(2700), vol=1.1, hats16=True, lead=[A3, C4, E4, A4 / 2 * 2, E4, C4])

# 10. The fix: drop to thinking, then riser into the boot
for b in range(int((F(2980) - F(2700)) / BEAT)):
    add(score, hat(0.05, 0.012), F(2700) + b * BEAT, 0.08)
add(score, pad([A2, E3, C4], F(2980) - F(2700) + 0.5, attack=1.5, release=0.5, bright=0.1), F(2700), 0.3)
add(score, riser(F(3050) - F(2980), 200, 1000), F(2980), 0.35)

# 11. It boots: major bloom
add(score, pad([A2, Cs3, E3, A3, Cs4, E4], 4.0, attack=0.02, release=2.5, bright=0.5), F(3052), 0.6)
add(score, kick(1.5, 120, 35, 0.5), F(3052), 0.7)
for i, n in enumerate([A4, Cs5, E5, A5]):
    add(score, bell(n), F(3052) + i * 0.09, 0.14)

# 12. Celebrate: bright pulse in A major
major = [(A2, [A2, Cs4, E4]), (E2, [E3, Gs3, B2 * 2]), (Fs3 / 2, [Fs3, A3, Cs4]), (D2, [D3, Fs3, A3])]
pulse_section(F(3150), F(3360), vol=0.9, chords=major, lead=[A3, Cs4, E4, Cs4])

# 13. Next line + title: warm, calm, fade out
add(score, pad([A2, E3, Cs4, E4], F(3960) - F(3355), attack=1.5, release=6, bright=0.25), F(3355), 0.45)
for i in range(14):
    n = [E4, Cs4, A3, B2 * 2, Cs4, E4, A4][i % 7]
    add(score, pluck(n, 2.0), F(3380) + i * 1.9, 0.12)
for i, n in enumerate([A4, E5, Cs5]):
    add(score, bell(n, 3.5), F(3600) + 2.2 + i * 2.4, 0.1)

score = reverb(score, 2.6, 0.7, 0.3)
end = int(F(3955) * SR)
score[end:] = 0
fo = int(3 * SR)
score[end - fo:end] *= np.linspace(1, 0, fo)
save('boot_score.wav', score[: int(TOTAL * SR)], 0.85)

# ---------------- sound effects ----------------


def clicks(dur, mean_gap, seed):
    r = np.random.default_rng(seed)
    buf = np.zeros(int(dur * SR))
    t = 0.05
    while t < dur - 0.05:
        n = int(0.012 * SR)
        tt = np.arange(n) / SR
        c = highpass(r.standard_normal(n), 2) * np.exp(-tt / 0.003)
        c += 0.4 * np.sin(2 * np.pi * r.uniform(2200, 3400) * tt) * np.exp(-tt / 0.004)
        if r.random() < 0.1:  # space bar thunk
            c = c * 0.5 + np.sin(2 * np.pi * 180 * tt) * np.exp(-tt / 0.01)
        add(buf, c, t, r.uniform(0.5, 1.0))
        t += mean_gap * r.uniform(0.4, 1.8)
    return buf


save('typing_slow.wav', reverb(clicks(10, 0.13, 1), 0.4, 0.08, 0.15), 0.8)
save('typing_fast.wav', reverb(clicks(10, 0.065, 2), 0.4, 0.08, 0.15), 0.8)

t = secs(0.75)
sq = np.sign(np.sin(2 * np.pi * 98 * t)) + np.sign(np.sin(2 * np.pi * 104 * t))
gate = ((t * 8) % 1 < 0.75).astype(float)
save('error_buzz.wav', smooth(sq, 4) * gate * fades(len(t), 0.005, 0.1), 0.6)

t = secs(2.5)
boom = kick(2.5, 160, 28, 0.55)
crack = smooth(rng.standard_normal(len(t)), 3) * np.exp(-t / 0.12)
save('impact.wav', reverb(np.tanh(2.5 * (boom + 0.6 * crack)), 2.0, 0.5, 0.3))

t = secs(2.0)
u = t / 2.0
swell = smooth(rng.standard_normal(len(t)), 8) * u ** 3
growl = np.sin(2 * np.pi * 46 * t + 2 * np.sin(2 * np.pi * 3 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 8 * t)) * u ** 2
save('shadow_swell.wav', np.tanh(1.5 * (swell + growl)) * fades(len(t), 0.05, 0.08), 0.8)

g = np.zeros(int(0.45 * SR))
for i in range(0, len(g), int(0.025 * SR)):
    seg = min(int(0.025 * SR), len(g) - i)
    tt = np.arange(seg) / SR
    g[i:i + seg] = np.sign(np.sin(2 * np.pi * rng.uniform(200, 2000) * tt)) * (rng.random() > 0.3)
save('glitch.wav', np.round(g * 4) / 4 * fades(len(g), 0.002, 0.05), 0.5)

t = secs(0.12)
save('beep.wav', np.sin(2 * np.pi * 1760 * t) * fades(len(t), 0.005, 0.05), 0.5)

t = secs(0.14)
f = 520 + 700 * (t / 0.14)
save('pop.wav', np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05) * fades(len(t), 0.002, 0.02), 0.7)

t = secs(0.2)
f = np.where(t < 0.07, 880, 1320)
save('day.wav', np.sin(2 * np.pi * np.cumsum(f) / SR) * fades(len(t), 0.003, 0.08), 0.45)

t = secs(0.9)
u = t / 0.9
n = rng.standard_normal(len(t))
wh = smooth(n, 30) * (1 - u) + highpass(n, 3) * u * 0.5
save('whoosh.wav', wh * np.sin(np.pi * u) ** 2, 0.6)

t = secs(0.14)
save('footstep.wav', (np.sin(2 * np.pi * 75 * t) * np.exp(-t / 0.035) + 0.15 * smooth(rng.standard_normal(len(t)), 10) * np.exp(-t / 0.02)), 0.7)

buf = np.zeros(int(2.8 * SR))
for i, nf in enumerate([A5, Cs5 * 2, E5 * 2, A5 * 2]):
    add(buf, bell(nf, 2.5), i * 0.08, 1.0)
save('success.wav', reverb(buf, 1.5, 0.4, 0.3), 0.7)

t = secs(0.12)
tick = highpass(rng.standard_normal(len(t)), 2) * np.exp(-t / 0.004) + 0.8 * np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.02)
save('type_tick.wav', tick, 0.7)


# ================================================================ ENIGMA
# New effects for the Enigma film.
t = secs(0.09)
save('tick.wav', highpass(rng.standard_normal(len(t)), 2) * np.exp(-t / 0.006) + 0.5 * np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.01), 0.6)

morse = np.zeros(int(3.2 * SR))
pos = 0.05
for sym in '-.-. --.- -.. .--. .-. .. -. --. .- ...'.replace(' ', '/'):
    if sym == '/':
        pos += 0.18
        continue
    d = 0.06 if sym == '.' else 0.18
    tt = secs(d)
    add(morse, np.sin(2 * np.pi * 750 * tt) * fades(len(tt), 0.004, 0.004), pos, 1.0)
    pos += d + 0.06
save('morse.wav', morse, 0.45)

t = secs(2.5)
save('sonar.wav', reverb(np.sin(2 * np.pi * 1180 * t) * np.exp(-t / 0.35) * fades(len(t), 0.003, 0.2), 2.0, 0.6, 0.45), 0.5)

# the Bombe: a dense mechanical clatter (many small clicks) over a motor hum, loops cleanly over 4 s
b = np.zeros(int(4 * SR))
tt = secs(0.012)
click = highpass(rng.standard_normal(len(tt)), 2) * np.exp(-tt / 0.003)
for k in range(int(4 / 0.045)):
    add(b, click, k * 0.045 + rng.uniform(0, 0.01), rng.uniform(0.3, 1.0))
tb = secs(4)
b += 0.25 * np.sin(2 * np.pi * 55 * tb) * (1 + 0.3 * np.sin(2 * np.pi * 7 * tb))
save('bombe.wav', b, 0.6)

t = secs(1.6)
save('chalk.wav', highpass(rng.standard_normal(len(t)), 3) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 3 * t))) * fades(len(t), 0.05, 0.2), 0.35)

t = secs(0.4)
save('stamp.wav', reverb(np.tanh(3 * (kick(0.4, 140, 50, 0.06) + 0.5 * smooth(rng.standard_normal(len(t)), 4) * np.exp(-t / 0.03))), 0.6, 0.15, 0.2), 0.8)

clink = np.zeros(int(0.9 * SR))
for k, f0 in enumerate([2900, 3600, 3300]):
    tt = secs(0.5)
    add(clink, np.sin(2 * np.pi * f0 * tt) * np.exp(-tt / 0.08), k * 0.11, 0.6)
save('chain.wav', clink, 0.5)

# Score for the Enigma film, timed to the narration (public/voice/enigma.json).
import json  # noqa: E402

vpath = os.path.join(os.path.dirname(__file__), '..', 'public', 'voice', 'enigma.json')
if os.path.exists(vpath):
    V = json.load(open(vpath))
    VOICE_AT = 20 / 30
    Ls = lambda n: V['lines'][n - 1]['start'] + VOICE_AT  # noqa: E731
    Le = lambda n: V['lines'][n - 1]['end'] + VOICE_AT  # noqa: E731
    title_at = round(V['duration'] * 30) / 30 + VOICE_AT + 20 / 30
    total = title_at + 12
    sc = np.zeros(int((total + 3) * SR))

    def put(sig, t0, vol):
        add(sc, sig, t0, vol)

    # cold open: low A minor drone, a slow clock-like tick, sparse high plucks
    put(pad([A1, E2, A2], Ls(10) + 0.2, attack=4, release=0.08, bright=0.25), 0, 0.55)
    for k in range(int(Ls(10) / 1.0)):
        put(hat(0.05, 0.01), 0.5 + k * 1.0, 0.06)
    for i, n in enumerate([E5, C5, A4, E4, F2 * 8, E4]):
        put(pluck(n, 2.2), 2 + i * 5.0, 0.1)
    put(riser(Ls(10) - Ls(9), 70, 300), Ls(9), 0.18)
    put(kick(2.0, 80, 28, 0.7), Ls(10) + 0.25, 0.8)  # "almost right": a low hit, then silence

    # the Atlantic: slow heavy pulse in D minor
    beat = 0.75
    t0, t1 = Ls(11) - 0.3, Le(17) + 0.6
    for k in range(int((t1 - t0) / beat)):
        put(kick(0.6, 70, 34, 0.25), t0 + k * beat, 0.45)
        if k % 4 == 0:
            put(pad([D2 * 2, F3 / 2 * 2, A2], beat * 4 + 0.4, attack=0.5, release=0.5, bright=0.2), t0 + k * beat, 0.35)
    put(pad([D4, D4 * 1.06], t1 - t0, attack=4, release=1, bright=0), t0, 0.05)

    # Bletchley: curious, lighter plucked arpeggio
    t0, t1 = Ls(18) - 0.3, Le(24) + 0.8
    arp = [A3, C4, E4, A4, E4, C4]
    k = 0
    while t0 + k * 0.3 < t1:
        put(pluck(arp[k % 6], 0.9), t0 + k * 0.3, 0.1)
        k += 1
    put(pad([A2, E3, C4], t1 - t0, attack=1.5, release=1, bright=0.2), t0, 0.3)

    # the struggle: tense ostinato, then a low sad pad
    t0, t1 = Ls(25) - 0.2, Ls(28)
    beat = 0.5
    for k in range(int((t1 - t0) / beat)):
        put(kick(), t0 + k * beat, 0.4)
        put(hat(), t0 + k * beat + beat / 2, 0.1)
        put(bass(A2 / 2 if (k // 4) % 2 == 0 else F2, beat), t0 + k * beat, 0.3)
    put(pad([A1, E2, C3], Le(28) - Ls(28) + 1.5, attack=1, release=1.2, bright=0.1), Ls(28), 0.5)

    # the flaw: rising arpeggios, building into the Bombe stopping
    t0, t1 = Ls(29) - 0.2, Ls(36)
    seq = [A3, C4, E4, G3 * 2, A4, C5]
    k = 0
    while t0 + k * 0.25 < t1:
        put(pluck(seq[k % 6] * (1 + 0.0 * k), 0.7), t0 + k * 0.25, 0.06 + 0.06 * (k * 0.25) / (t1 - t0))
        k += 1
    put(pad([A2, E3, C4, E4], t1 - t0, attack=3, release=0.3, bright=0.3), t0, 0.35)
    hit = Ls(37) - 6 / 30
    put(riser(hit - Ls(36), 120, 700), Ls(36), 0.3)

    # the breakthrough: major bloom, then warm and reflective to the end
    put(kick(1.8, 110, 32, 0.6), hit, 0.7)
    put(pad([A2, Cs3, E3, A3, Cs4, E4], 6, attack=0.02, release=3, bright=0.45), hit, 0.6)
    for i, n in enumerate([A4, Cs5, E5, A5]):
        put(bell(n), hit + i * 0.1, 0.12)
    t0 = hit + 4
    put(pad([A2, E3, Cs4, E4], total - t0, attack=2, release=7, bright=0.25), t0, 0.42)
    for i in range(int((total - t0) / 1.9)):
        put(pluck([E4, Cs4, A3, B2 * 2, Cs4, E4, A4][i % 7], 2.0), t0 + i * 1.9, 0.1)
    for i, n in enumerate([A4, E5, Cs5]):
        put(bell(n, 3.5), title_at + 2.2 + i * 2.4, 0.1)

    sc = reverb(sc, 2.6, 0.7, 0.3)
    end = int((total - 0.2) * SR)
    sc[end:] = 0
    sc[end - 3 * SR:end] *= np.linspace(1, 0, 3 * SR)
    save('enigma_score.wav', sc[: int(total * SR)], 0.85)


# ================================================================ MOTH
# New effects for the Moth film (Harvard Mark II, 1947). All synthesised here.
def relay_click(seed=0, bright=1.0):
    r = np.random.default_rng(seed)
    tt = secs(0.06)
    c = highpass(r.standard_normal(len(tt)), 2) * np.exp(-tt / 0.004)
    c += 0.6 * bright * np.sin(2 * np.pi * r.uniform(3000, 4200) * tt) * np.exp(-tt / 0.006)
    c += 0.5 * np.sin(2 * np.pi * 420 * tt) * np.exp(-tt / 0.012)
    return c


rel = np.zeros(int(0.35 * SR))
add(rel, relay_click(1), 0.0, 1.0)
add(rel, relay_click(2, 0.6), 0.012, 0.35)  # contact bounce
save('relay.wav', reverb(rel, 0.4, 0.1, 0.2), 0.7)

# the relay bank: hundreds of small clicks, 10 s, no hum
bank = np.zeros(int(10 * SR))
r = np.random.default_rng(11)
tt0 = 0.0
while tt0 < 9.9:
    add(bank, relay_click(int(r.integers(0, 50)), r.uniform(0.3, 1.0)), tt0, r.uniform(0.15, 0.6))
    tt0 += r.exponential(0.035)
save('relay_bank.wav', reverb(bank, 0.6, 0.2, 0.25) * fades(len(bank), 0.3, 0.5), 0.55)

# a relay buzzing against something stuck in it
st = np.zeros(int(0.8 * SR))
for k in range(9):
    add(st, relay_click(20 + k, 0.4), k * 0.028, 0.6 * (1 - k / 10))
t = secs(0.8)
st += 0.25 * np.sign(np.sin(2 * np.pi * 60 * t)) * np.exp(-t / 0.25) * fades(len(t), 0.01, 0.2)
save('relay_stuck.wav', smooth(st, 2), 0.55)

# moth wings: soft noise flutter ~22 Hz
t = secs(1.4)
fl = smooth(rng.standard_normal(len(t)), 30) * (0.5 + 0.5 * np.sin(2 * np.pi * 22 * t)) ** 2
save('flutter.wav', fl * fades(len(t), 0.25, 0.5), 0.35)

# marker pen squeak on paper
t = secs(0.45)
f = 1500 + 400 * np.sin(2 * np.pi * 3 * t)
sq = 0.3 * np.sin(2 * np.pi * np.cumsum(f) / SR) + highpass(rng.standard_normal(len(t)), 3) * 0.7
save('marker.wav', sq * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t)) * fades(len(t), 0.03, 0.12), 0.3)

# pen writing: scratchy, rhythmic
t = secs(1.6)
pen = highpass(rng.standard_normal(len(t)), 2) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 4.5 * t)) ** 3)
save('pen.wav', pen * fades(len(t), 0.05, 0.3), 0.25)

# page turn / slide
t = secs(0.7)
u = t / 0.7
save('page.wav', smooth(rng.standard_normal(len(t)), 6) * np.sin(np.pi * u) ** 2 * (1 + 0.5 * np.sin(2 * np.pi * 30 * t)), 0.4)

# tweezers: small metallic tick
t = secs(0.3)
save('tweezer.wav', reverb(np.sin(2 * np.pi * 5200 * t) * np.exp(-t / 0.02) + 0.5 * np.sin(2 * np.pi * 7400 * t) * np.exp(-t / 0.01), 0.4, 0.1, 0.2), 0.45)

# tape: a short sticky rip
t = secs(0.5)
crack = np.zeros(len(t))
for k in range(int(len(t) / (0.004 * SR))):
    if rng.random() < 0.55:
        i = int(k * 0.004 * SR)
        crack[i:i + 60] += rng.uniform(0.3, 1.0) * np.exp(-np.arange(min(60, len(t) - i)) / 12)
save('tape.wav', highpass(crack, 2) * fades(len(t), 0.02, 0.15), 0.5)

# applause: thousands of soft claps
save('applause.wav', reverb(clicks(4, 0.004, 9), 1.2, 0.3, 0.35) * fades(int(4 * SR), 0.6, 1.4), 0.5)

# Score for the Moth film, timed to the narration (public/voice/moth.json).
mpath = os.path.join(os.path.dirname(__file__), '..', 'public', 'voice', 'moth.json')


def moth_score():
    V = json.load(open(mpath))
    VA = 20 / 30
    Ls = lambda n: V['lines'][n - 1]['start'] + VA  # noqa: E731
    Le = lambda n: V['lines'][n - 1]['end'] + VA  # noqa: E731
    title_at = round(V['duration'] * 30) / 30 + VA + 20 / 30
    total = title_at + 12
    sc = np.zeros(int((total + 3) * SR))

    def put(sig, t0, vol):
        add(sc, sig, t0, vol)

    D2_, F2_, G2_, A2_, Bb2 = 73.42, 87.31, 98.0, 110.0, 116.54
    D3_, F3_, G3_, A3_, Bb3, C4_ = 146.83, 174.61, 196.0, 220.0, 233.08, 261.63
    D4_, E4_, F4_, G4_, A4_, C5_, D5_, Fs4, Fs3 = 293.66, 329.63, 349.23, 392.0, 440.0, 523.25, 587.33, 369.99, 185.0

    # cold open: low D minor drone, a slow relay-like tick, sparse high plucks
    t1 = Ls(9) - 0.3
    put(pad([D2_, A2_, D3_], t1, attack=3, release=1.5, bright=0.2), 0, 0.5)
    for k in range(int(t1 / 1.0)):
        put(hat(0.04, 0.008), 0.5 + k * 1.0, 0.05)
    for i, n in enumerate([A4_, F4_, D4_, E4_, C5_, A4_]):
        put(pluck(n, 2.2), 1.5 + i * 4.5, 0.09)
    put(kick(2.0, 80, 28, 0.7), Le(8) + 0.3, 0.6)  # "tells it wrong": a low hit

    # part I, the machine: a curious mechanical pulse (soft clicks + plucked arpeggio)
    t0, t1 = Ls(9) - 0.2, Le(16) + 0.4
    arp = [D3_, F3_, A3_, D4_, A3_, F3_, Bb2 * 2, D4_]
    k = 0
    while t0 + k * 0.3 < t1:
        put(pluck(arp[k % 8], 0.9), t0 + k * 0.3, 0.08)
        put(hat(0.03, 0.006), t0 + k * 0.3 + 0.15, 0.04)
        k += 1
    put(pad([D2_, A2_, F3_], t1 - t0, attack=2, release=1, bright=0.2), t0, 0.32)
    put(pad([D2_, A2_, D3_], Le(17) - Le(16) + 0.8, attack=0.5, release=1, bright=0.1), Le(16), 0.45)

    # part II, the hunt: tense pulse that builds, then stops dead on the moth
    t0, hit = Ls(18) - 0.3, Ls(22) - 0.2
    beat = 0.5
    n = int((hit - t0) / beat)
    for k in range(n):
        g = 0.6 + 0.4 * k / max(1, n)
        put(kick(0.5, 90, 38, 0.18), t0 + k * beat, 0.4 * g)
        put(hat(), t0 + k * beat + beat / 2, 0.07 * g)
        put(bass(D2_ if (k // 4) % 2 == 0 else Bb2 / 2, beat), t0 + k * beat, 0.28 * g)
    put(riser(hit - Ls(21), 120, 600), Ls(21), 0.22)
    put(kick(1.6, 70, 30, 0.6), hit, 0.6)
    put(pad([D4_, D4_ * 1.5], Ls(24) - hit, attack=1.5, release=1.0, bright=0), hit + 0.4, 0.1)

    # the moth comes out and goes into the log: soft bells over a warm pad
    t0, t1 = Ls(24) - 0.2, Le(26) + 0.8
    put(pad([D3_, F3_, A3_], t1 - t0, attack=1.5, release=1.0, bright=0.2), t0, 0.3)
    for i, n in enumerate([A4_, F4_, D4_, A4_, C5_]):
        put(bell(n, 3), t0 + 0.5 + i * 1.6, 0.07)

    # part III, the twist: lighter, plucky, a little wry (F major)
    t0, t1 = Ls(27) - 0.3, Le(31) + 0.6
    pat = [F3_, A3_, C4_, A3_, G3_, Bb3, D4_, Bb3]
    k = 0
    while t0 + k * 0.25 < t1:
        if k % 8 not in (3, 7):
            put(pluck(pat[k % 8], 0.5), t0 + k * 0.25, 0.08)
        k += 1
    put(pad([F2_, C4_ / 2, A3_], t1 - t0, attack=1.5, release=1, bright=0.2), t0, 0.28)
    for i in range(int((t1 - t0) / 1.0)):
        put(kick(0.4, 80, 40, 0.1), t0 + i * 1.0, 0.25)

    # part IV, the storyteller: warm D major
    t0, t1 = Ls(32) - 0.3, Le(36) + 0.8
    put(pad([D3_, Fs3, A3_, D4_], t1 - t0, attack=2, release=1.5, bright=0.25), t0, 0.35)
    for i in range(int((t1 - t0) / 1.5)):
        put(pluck([D4_, Fs4, A4_, Fs4, E4_, D4_][i % 6], 1.8), t0 + i * 1.5, 0.08)

    # what happened next: reflective, to the end
    t0 = Ls(37) - 0.3
    put(pad([D2_, A2_, Fs3, A3_], total - t0, attack=2.5, release=6, bright=0.2), t0, 0.38)
    for i in range(int((title_at - t0) / 2.0)):
        put(pluck([A4_, Fs4, D4_, E4_, Fs4, D5_ / 2][i % 6], 2.0), t0 + i * 2.0, 0.08)
    for i, n in enumerate([D4_ * 2, A4_, Fs4 * 2]):
        put(bell(n, 3.5), title_at + 2.2 + i * 2.4, 0.09)

    sc = reverb(sc, 2.6, 0.7, 0.3)
    end = int((total - 0.2) * SR)
    sc[end:] = 0
    sc[end - 3 * SR:end] *= np.linspace(1, 0, 3 * SR)
    save('moth_score.wav', sc[: int(total * SR)], 0.85)


if os.path.exists(mpath):
    moth_score()


# ================================================================ TAUM SAUK
# New effects for the Taum Sauk film (reservoir failure, 2005). All synthesised here.
def lowpass(x, k):
    return smooth(smooth(x, k), k)


# pump hum: a low 60 Hz machine drone with a slow beat, 12 s, loopable fades
t = secs(12)
hum = (np.sin(2 * np.pi * 60 * t) + 0.5 * np.sin(2 * np.pi * 120 * t + 0.3) + 0.2 * np.sin(2 * np.pi * 180.6 * t)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.4 * t))
hum += 0.15 * lowpass(rng.standard_normal(len(t)), 40)
save('pump_hum.wav', hum * fades(len(t), 0.6, 0.8), 0.45)

# rushing water: broadband noise, slowly swelling, low-passed, 10 s
t = secs(10)
rush = lowpass(rng.standard_normal(len(t)), 6) + 0.6 * lowpass(rng.standard_normal(len(t)), 30)
rush *= 0.75 + 0.25 * smooth(rng.standard_normal(len(t)), 9000) * 8
save('water_rush.wav', reverb(rush, 1.5, 0.4, 0.3) * fades(len(t), 0.8, 1.0), 0.6)

# trickle: water spilling over an edge, bright bubbly noise, 6 s
t = secs(6)
tr = highpass(rng.standard_normal(len(t)), 3) * 0.3
bub = np.zeros(len(t))
r = np.random.default_rng(31)
tb = 0.0
while tb < 5.9:
    n = int(0.03 * SR)
    tt = np.arange(n) / SR
    f0 = r.uniform(700, 1800)
    add(bub, np.sin(2 * np.pi * np.cumsum(f0 * (1 + 2 * tt / 0.03)) / SR) * np.exp(-tt / 0.008), tb, r.uniform(0.2, 0.6))
    tb += r.exponential(0.025)
save('trickle.wav', reverb(tr + bub, 0.8, 0.2, 0.3) * fades(len(t), 0.4, 0.8), 0.4)

# rumble: the wall giving way, deep sub-bass roll with crackle, 5 s
t = secs(5)
rum = lowpass(rng.standard_normal(len(t)), 120) * 30 * np.exp(-t / 1.8)
rum += 0.5 * np.sin(2 * np.pi * np.cumsum(38 + 10 * np.exp(-t)) / SR) * np.exp(-t / 1.5)
crk = clicks(5, 0.02, 41) * np.exp(-t / 1.2) * 0.4
save('rumble.wav', np.tanh(1.8 * reverb(rum + crk, 2.0, 0.6, 0.3)) * fades(len(t), 0.02, 1.0), 0.8)

# creak: metal bracket straining, a slow bowed squeal, 1.6 s
t = secs(1.6)
fq = 180 + 60 * np.sin(2 * np.pi * 0.7 * t) + 30 * smooth(rng.standard_normal(len(t)), 800) * 10
cr = np.sign(np.sin(2 * np.pi * np.cumsum(fq) / SR)) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t))
save('creak.wav', reverb(lowpass(cr, 6), 0.8, 0.25, 0.25) * fades(len(t), 0.15, 0.4), 0.35)

# night: soft crickets and air, 10 s
t = secs(10)
nt = 0.25 * lowpass(rng.standard_normal(len(t)), 60)
for k, (f0, rate, ph) in enumerate([(4300, 2.6, 0.0), (4700, 3.1, 1.3), (3900, 2.2, 2.1)]):
    chirp = (np.sin(2 * np.pi * rate * t + ph) > 0.6) * (0.5 + 0.5 * np.sin(2 * np.pi * 45 * t))
    nt += 0.08 * np.sin(2 * np.pi * f0 * t) * smooth(chirp.astype(float), 200)
save('night.wav', nt * fades(len(t), 1.0, 1.5), 0.3)

# Score for the Taum Sauk film, timed to the narration (public/voice/taumsauk.json).
tpath = os.path.join(os.path.dirname(__file__), '..', 'public', 'voice', 'taumsauk.json')


def taumsauk_score():
    V = json.load(open(tpath))
    VA = 20 / 30
    Ls = lambda n: V['lines'][n - 1]['start'] + VA  # noqa: E731
    Le = lambda n: V['lines'][n - 1]['end'] + VA  # noqa: E731
    title_at = round(V['duration'] * 30) / 30 + VA + 20 / 30
    total = title_at + 12
    sc = np.zeros(int((total + 3) * SR))

    def put(sig, t0, vol):
        add(sc, sig, t0, vol)

    E1, B1, E2, G2_, A2_, B2_, C3_, D3_, E3_ = 41.2, 61.74, 82.41, 98.0, 110.0, 123.47, 130.81, 146.83, 164.81
    Fs3, G3_, A3_, B3_, D4_, E4_, Fs4, G4_, A4_, B4_ = 185.0, 196.0, 220.0, 246.94, 293.66, 329.63, 369.99, 392.0, 440.0, 493.88

    # cold open: low E minor drone, slow drips of piano-like plucks, a dark hit on "asleep"
    t1 = Ls(8) - 0.3
    put(pad([E2, B2_, E3_], t1, attack=3, release=1.5, bright=0.2), 0, 0.5)
    for i, n in enumerate([B3_, G3_, E3_, Fs3, G3_, B3_, A3_]):
        put(pluck(n * 2, 2.4), 1.0 + i * 3.6, 0.08)
    put(kick(2.0, 80, 28, 0.7), Ls(3) - 0.1, 0.45)
    put(kick(2.0, 80, 28, 0.7), Le(7) + 0.2, 0.55)

    # part I, the battery: a steady mechanical pulse (pumps), curious and even
    t0, t1 = Ls(8) - 0.2, Le(14) + 0.4
    arp = [E3_, G3_, B3_, E4_, B3_, G3_, D4_, B3_]
    k = 0
    while t0 + k * 0.32 < t1:
        put(pluck(arp[k % 8], 0.9), t0 + k * 0.32, 0.07)
        put(hat(0.03, 0.006), t0 + k * 0.32 + 0.16, 0.035)
        k += 1
    put(pad([E2, B2_, G3_], t1 - t0, attack=2, release=1, bright=0.2), t0, 0.3)
    put(pad([C3_, G3_, E4_], Ls(16) - Le(14), attack=0.3, release=1, bright=0.1), Le(14), 0.35)

    # part II, the gauges: uneasy, a slow ticking pulse with a dissonant shimmer
    t0, t1 = Ls(16) - 0.3, Le(23) + 0.5
    for k in range(int((t1 - t0) / 0.75)):
        put(kick(0.4, 70, 36, 0.12), t0 + k * 0.75, 0.25)
    put(pad([E2, B2_, C3_ * 2], t1 - t0, attack=2, release=1.2, bright=0.25), t0, 0.32)
    put(pad([B4_, 523.25], t1 - Ls(20), attack=3, release=1.5, bright=0), Ls(20), 0.06)
    put(kick(1.6, 70, 30, 0.6), Le(23) + 0.2, 0.5)

    # part III, the night: a heartbeat pulse that builds to the overtopping, then stops dead
    t0, hit = Ls(25) - 0.3, Ls(29) + 52 / 30
    beat = 0.6
    n = int((hit - t0) / beat)
    for k in range(n):
        g = 0.5 + 0.5 * k / max(1, n)
        put(kick(0.5, 90, 38, 0.18), t0 + k * beat, 0.4 * g)
        put(bass(E2 if (k // 4) % 2 == 0 else C3_ / 2, beat), t0 + k * beat, 0.25 * g)
        if k % 2:
            put(hat(), t0 + k * beat, 0.05 * g)
    put(pad([E2, B2_, E3_], hit - t0, attack=2, release=0.3, bright=0.3), t0, 0.3)
    put(riser(hit - Ls(28), 120, 700), Ls(28), 0.2)
    put(kick(2.4, 60, 24, 0.9), hit, 0.75)

    # the flood: low, heavy, dark swells
    t0, t1 = hit + 0.5, Ls(34) - 0.4
    put(pad([E1 * 2, B1 * 2, E2], t1 - t0, attack=1.5, release=1.5, bright=0.4), t0, 0.45)
    put(pad([E3_, Fs3, G3_], t1 - t0, attack=3, release=1.5, bright=0), t0 + 1, 0.08)

    # all five survived: a soft turn into G major
    t0, t1 = Ls(34) - 0.3, Le(35) + 1.0
    put(pad([G2_, D3_, B3_, D4_], t1 - t0, attack=1.2, release=1.2, bright=0.25), t0, 0.38)
    for i, nn in enumerate([B4_, G4_, D4_, G4_]):
        put(bell(nn, 3), t0 + 0.6 + i * 1.4, 0.07)

    # aftermath: reflective E minor to G, sparse, then title bells
    t0 = Ls(36) - 0.3
    put(pad([E2, B2_, G3_, B3_], total - t0, attack=2.5, release=6, bright=0.2), t0, 0.34)
    for i in range(int((title_at - t0) / 2.0)):
        put(pluck([B3_, G3_, E3_, Fs3, G3_, D4_][i % 6] * 2, 2.0), t0 + i * 2.0, 0.07)
    for i, nn in enumerate([E4_ * 2, B4_, G4_ * 2]):
        put(bell(nn, 3.5), title_at + 2.2 + i * 2.4, 0.09)

    sc = reverb(sc, 2.6, 0.7, 0.3)
    end = int((total - 0.2) * SR)
    sc[end:] = 0
    sc[end - 3 * SR:end] *= np.linspace(1, 0, 3 * SR)
    save('taumsauk_score.wav', sc[: int(total * SR)], 0.85)


if os.path.exists(tpath):
    taumsauk_score()
