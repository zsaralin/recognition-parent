import math
import time

class OneEuroFilter:
    def __init__(self, freq, min_cutoff=1.0, beta=0.0, d_cutoff=500.0):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None

    def alpha(self, cutoff):
        tau = 1.0 / (2 * math.pi * cutoff)
        te = 1.0 / self.freq
        return 1.0 / (1.0 + tau / te)

    def filter(self, x, t=None):
        if self.t_prev is None:
            self.t_prev = t
            self.x_prev = x
            self.dx_prev = 0.0
            return x

        # Calculate the time difference
        te = t - self.t_prev
        self.freq = 1.0 / te

        # Derivative of the signal
        dx = (x - self.x_prev) * self.freq
        dx_hat = self.dx_prev + self.alpha(self.d_cutoff) * (dx - self.dx_prev)

        # Update the cutoff frequency based on the speed of the signal
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)

        # Filter the signal
        x_hat = self.x_prev + self.alpha(cutoff) * (x - self.x_prev)

        # Update previous values
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t

        return x_hat
