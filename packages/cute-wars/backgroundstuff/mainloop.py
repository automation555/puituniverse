import os
import math

from pyglet import font
from pyglet import window
from pyglet import clock
from pyglet import media
from pyglet import image
from pyglet.gl import *
from backgroundstuff import graphics

from backgroundstuff.fixed_resolution import FixedResolutionViewport
from backgroundstuff.boundingbox import Boundingbox


scale_factor = 3 # OOPS: this should be set to 3 when i do the commit ...
width = 200
height = 120

class Mainloop(window.Window):
  _max_scroll_speed = 8 # pixels per tick

  def __init__(self):
    super(Mainloop, self).__init__(width*scale_factor, height*scale_factor, 'puit')
    
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    self.viewport = FixedResolutionViewport(self, width, height, filtered=False) #base resolution we're working in

    self.font = font.load('Arial', 10)
    self.media = {}

    self.scrollarea = Boundingbox(size=(width, height))
    self._scroll_speed = (0, 0)
    self.state = None
    
  def scroll_to(self, new_position):
    old_position = self.scrollarea.bottom_left
    self.scrollarea.move(self._get_scroll_delta(old_position, new_position))
    # TODO: stupid scrolling system
    # i'd like to move the code that limits the scrollarea to the extents
    # of the level over here. however, a Mainloop doesn't necessarily have
    # to run a Level instance, so maybe we need a concept like "all-encompassing
    # Gameobject"?

  def draw_text(self, text, position):
    t = font.Text(self.font, text, position[0], position[1])
    t.draw()
  
  def play(self, filename):
    if not self.media.has_key(filename):
      self.media[filename] = media.load(os.path.join('data', filename), streaming=False)
    self.media[filename].play()

  def on_key_press(self, symbol, modifiers):
    self.state.on_key_press(symbol, modifiers)

  def on_key_release(self, symbol, modifiers):
    self.state.on_key_release(symbol, modifiers)

  def run(self):
    clock.set_fps_limit(30)
    sim_time = 0.0
    real_time = 0.0
    frames_skipped = 0
    while not self.has_exit:
      real_time += clock.tick()
      self.dispatch_events()
      media.dispatch_events()
      draw = sim_time >= real_time
      if frames_skipped >= 1:
        draw = True
        frames_skipped = 0
        real_time = sim_time
      self.tick(draw)
      if not draw:
        frames_skipped += 1
      sim_time += 1 / 30.0
      # print 'FPS is %f' % clock.get_fps()
  
  def tick(self, draw=True):
    # having the core functionality of the run loop in its own method helps
    # with adding stuff here in subclasses.
    self.state.update(draw)

  def please_quit(self):
    self.has_exit = True
  
  def _get_scroll_delta(self, old_position, new_position):
    def round_to_larger_magnitude(x):
      if x >= 0:
        return math.ceil(x)
      else:
        return math.floor(x)
    
    def throttle(target, limiter):
      # first of all, don't bother with tiny targets!
      if abs(target) < 1:
        return 0
      # if target and limiter have same sign, implement our heuristic:
      if (target >= 0) == (limiter >= 0):
        # in case limiter is too small, make an exception:
        if (target >= 1.0) and (limiter < 0.5):
          limiter = 1.0
        elif (target <= -1.0) and (limiter > -0.5):
          limiter -1.0
        limiter *= 2.0
        if abs(target) <= abs(limiter):
          return target
        else:
          return limiter
      else:
        # but if target and limiter have different signs, do the visually
        # least jarring thing:
        limiter /= 2.0
        if abs(limiter) < 1.5:
          if target >= 0:
            return 1
          else:
            return -1
        return limiter
    
    # only cover at most half the distance in one tick (except if we're just
    # one pixel off -- we're rounding up for that reason); this dampens
    # small erratic movements when they occur in quick succession, and makes
    # transitions to other places of the map more graceful.
    delta_x = round_to_larger_magnitude((new_position[0] - old_position[0]) / 2.0)
    delta_y = round_to_larger_magnitude((new_position[1] - old_position[1]) / 2.0)
    delta = math.sqrt((delta_x ** 2) + (delta_y ** 2))
    # limit maximum scrolling distance per tick:
    if delta > self._max_scroll_speed:
      r = self._max_scroll_speed / delta
      delta_x *= r
      delta_y *= r
    # the other half of the 'graceful transitions' formula is to build speed
    # up slowly in addition to slowing down gently. we do this by remembering
    # the previous scrolling speed, which is simplistic, but sufficient:
    delta_x = throttle(delta_x, self._scroll_speed[0])
    delta_y = throttle(delta_y, self._scroll_speed[1])
    self._scroll_speed = (delta_x, delta_y)
    return self._scroll_speed
    # // _get_scroll_delta
  # // class Mainloop

class CameraTarget(object):
  LEFT = 0
  RIGHT = 1
  
  def __init__(self, x, y, facing=None):
    self.x = x
    self.y = y
    self.facing = facing