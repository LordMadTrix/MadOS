"""
MadOS - son de demarrage "Braise" (genere, donc libre de droits).

Accord de re majeur egrene (re, la, re, fa#) au timbre de cloche douce,
nappe grave, leger chorus et reverberation ; ~3 s, WAV 44,1 kHz 16 bits
stereo, normalise a -3 dBFS.
Sortie : media/sounds/MadOS_Startup.wav
"""
import math
import random
import struct
import wave

from mados_common import TREE

OUT = TREE / "media/sounds/MadOS_Startup.wav"
RATE = 44100
LENGTH = 3.2


def bell(t, f):
    """Cloche douce : fondamentale + partiels faibles, attaque courte, decroissance."""
    if t < 0:
        return 0.0
    attack = min(1.0, t / 0.012)
    env = attack * math.exp(-t * 1.9)
    return env * (math.sin(2 * math.pi * f * t)
                  + 0.30 * math.sin(2 * math.pi * 2.0 * f * t) * math.exp(-t * 3.5)
                  + 0.12 * math.sin(2 * math.pi * 3.01 * f * t) * math.exp(-t * 6.0))


def render():
    notes = [(0.00, 293.66, -0.35), (0.13, 440.00, 0.30), (0.26, 587.33, -0.15), (0.40, 739.99, 0.35)]
    n = int(RATE * LENGTH)
    left, right = [0.0] * n, [0.0] * n
    for i in range(n):
        t = i / RATE
        l = r = 0.0
        for start, f, pan in notes:
            s = bell(t - start, f) + 0.5 * bell(t - start, f * 1.003)   # leger chorus
            l += s * (1 - pan) * 0.5
            r += s * (1 + pan) * 0.5
        pad = 0.18 * min(1.0, t / 0.6) * math.exp(-max(0.0, t - 0.6) * 1.4) * (
            math.sin(2 * math.pi * 146.83 * t) + 0.5 * math.sin(2 * math.pi * 220.0 * t))
        left[i] = l + pad
        right[i] = r + pad
    # reverberation : quelques echos decroissants decales a gauche et a droite
    random.seed(7)
    for delay, gain in ((0.031, 0.32), (0.047, 0.27), (0.071, 0.21), (0.113, 0.15), (0.167, 0.10)):
        d = int(delay * RATE)
        for i in range(n - 1, d - 1, -1):
            left[i] += gain * right[i - d]
            right[i] += gain * left[i - d - 7 if i - d - 7 >= 0 else 0]
    # fondu de sortie et normalisation a -3 dBFS
    fade = int(0.5 * RATE)
    for i in range(n - fade, n):
        k = (n - i) / fade
        left[i] *= k
        right[i] *= k
    peak = max(max(abs(x) for x in left), max(abs(x) for x in right))
    scale = (10 ** (-3 / 20)) * 32767 / peak
    frames = bytearray()
    for l, r in zip(left, right):
        frames += struct.pack("<hh", int(l * scale), int(r * scale))
    return bytes(frames)


def main():
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(render())
    print(f"Son de demarrage : {OUT.relative_to(TREE)} ({LENGTH} s)")


if __name__ == "__main__":
    main()
