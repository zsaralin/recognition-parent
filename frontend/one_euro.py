import math
import time

class OneEuroFilter:
    def __init__(self, freq, mincutoff=1.0, beta=0.0, dcutoff=1.0):
        self.freq = freq
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.last_time = None
        self.x_prev = None
        self.dx_prev = None

    def alpha(self, cutoff):
        tau = 1.0 / (2 * math.pi * cutoff)
        te = 1.0 / self.freq
        return 1.0 / (1.0 + tau / te)

    def update(self, x):
        current_time = time.time()
        if self.last_time is None:
            self.last_time = current_time

        dt = current_time - self.last_time
        self.last_time = current_time
        self.freq = 1.0 / dt if dt > 0 else self.freq

        dx = 0.0 if self.x_prev is None else (x - self.x_prev) * self.freq
        edx = dx if self.dx_prev is None else self.dx_prev + self.alpha(self.dcutoff) * (dx - self.dx_prev)

        cutoff = self.mincutoff + self.beta * abs(edx)
        alpha = self.alpha(cutoff)

        x_hat = x if self.x_prev is None else self.x_prev + alpha * (x - self.x_prev)

        self.x_prev = x_hat
        self.dx_prev = edx

        return x_hat
