"""
PID implementation based on posts in this series:
http://brettbeauregard.com/blog/2011/04/improving-the-beginners-pid-introduction/
"""

import time


def millis():
    """returns current time as milliseconds"""
    return int(round(time.time() * 1000))


def clamp(value, min_val, max_val):
    """clamps a value between min and max"""
    if value > max_val:
        value = max_val
    elif value < min_val:
        value = min_val

    return value


class PidController(object):
    # pid implentation warrants several attributes
    # pylint: disable=R0902
    AUTO_MODE = 1
    MANUAL_MODE = 0

    # args: set_point, kp, ki, kd, sample_time_ms
    def __init__(self, **kwargs):
        # kwargs should be: {'mode': 1, 'kd': 0.01, 'ki': 0.01, 'kp': 2,
        # 'set_point': 160} or {'mode': 0, "output": 75}
        self.last_time = 0  # last time the pid function was calculated
        self.i_term = 0  # intergral term
        self.last_input = 0  # last input reading value
        self.kp = 0  # proportional gain
        self.ki = 0  # integral gain
        self.kd = 0  # derivative gain
        self.set_point = kwargs["set_point"]
        self.sample_time_ms = kwargs["sample_time_ms"]
        self.min_out = 0
        # by default the pid will return "duty cycle" between 0-100%
        self.max_out = 100
        self.mode = kwargs["mode"]
        self.input = 0
        self.output = 0
        self.full_cycle_threshold = kwargs.get(
            'full_cycle_threshold', float('inf'))

        if self.mode == PidController.AUTO_MODE:
            self.set_params(kwargs["kp"], kwargs["ki"], kwargs["kd"])
        else:
            self.set_mode(PidController.MANUAL_MODE)
            self.output = kwargs["output"]

    def update_config(self, config):
        self.mode = config["mode"]
        self.set_point = config["set_point"]

        if self.mode == PidController.AUTO_MODE:
            self.set_params(config["kp"], config["ki"], config["kd"])
        else:
            self.output = config["output"]

        self.full_cycle_threshold = config.get(
            'full_cycle_threshold', float('inf'))

        self.set_mode(self.mode)

    def set_mode(self, mode):
        move_to_auto = self.mode == PidController.MANUAL_MODE and mode == PidController.AUTO_MODE
        if move_to_auto:
            self.reinitialize()

        self.mode = mode

    def reinitialize(self):
        self.last_input = self.input
        self.i_term = clamp(self.output, self.min_out, self.max_out)

    def set_params(self, kp, ki, kd):
        sample_time_seconds = self.sample_time_ms / 1000.0
        self.kp = kp
        self.ki = ki * sample_time_seconds
        self.kd = kd / sample_time_seconds

    def set_output_limits(self, min_output, max_output):
        if min_output > max_output:
            return

        self.min_out = min_output
        self.max_out = max_output

        # clamp running total to min/max
        self.i_term = clamp(self.i_term, self.min_out, self.max_out)

    def update_sample_time(self, sample_time_ms):
        if sample_time_ms > 0:
            ratio = sample_time_ms / self.sample_time_ms
            self.ki *= ratio
            self.kd /= ratio

            self.sample_time_ms = sample_time_ms

    def compute(self):
        if self.mode == PidController.MANUAL_MODE:
            # just return, output should already be set in manual
            return True

        if self.input is None:
            print "PID Auto mode requires an input value, not calculating."
            return False

        # calc error
        error = self.set_point - self.input

        if error > self.full_cycle_threshold:
            # if the error is greater than the full_cycle_threshold,
            # just full cycle
            self.output = self.max_out
            return True

        # calculate time since last compute
        now = millis()
        time_change = now - self.last_time

        if time_change >= self.sample_time_ms:
            # add to running error total
            self.i_term += (self.ki * error)
            # clamp to min/max
            self.i_term = clamp(self.i_term, self.min_out, self.max_out)

            # input derivative
            d_input = self.input - self.last_input

            # save things for next time
            self.last_input = self.input
            self.last_time = now

            self.output = clamp(
                self.kp * error + self.i_term -
                self.kd * d_input, self.min_out,
                self.max_out)

            return True
        else:
            return False
