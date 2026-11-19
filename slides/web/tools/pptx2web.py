#!/usr/bin/env python3
"""pptx2web - convert a PowerPoint deck (.pptx) into a static, animated HTML presentation.

Every slide is rebuilt as absolutely positioned HTML/SVG on a 1920x1080 canvas, using the
deck's theme, masters and layouts.  Entrance/exit/emphasis animations, media triggers and
slide transitions are read from the slide timing trees and replayed in the browser with the
Web Animations API.  The output folder is a static site (index.html + assets/) that can be
served from GitHub Pages or any web server.

Usage: python pptx2web.py deck.pptx outdir --title "..." [--media-dir transcoded/] [--include-hidden]
"""
import argparse, colorsys, hashlib, html, io, json, math, os, posixpath, re, shutil, subprocess, sys, tempfile, zipfile
from lxml import etree
from PIL import Image, ImageColor, ImageEnhance, ImageOps

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'p14': 'http://schemas.microsoft.com/office/powerpoint/2010/main',
    'p15': 'http://schemas.microsoft.com/office/powerpoint/2012/main',
    'a14': 'http://schemas.microsoft.com/office/drawing/2010/main',
    'a16': 'http://schemas.microsoft.com/office/drawing/2014/main',
    'asvg': 'http://schemas.microsoft.com/office/drawing/2016/SVG/main',
    'adec': 'http://schemas.microsoft.com/office/drawing/2017/decorative',
}
RNS = NS['r']


def Q(t):
    p, l = t.split(':')
    return '{%s}%s' % (NS[p], l)


def ln(e):
    return etree.QName(e).localname if isinstance(e.tag, str) else ''


def f2(v):
    """compact float formatting"""
    if v is None:
        return '0'
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def esc(s):
    return html.escape(s, quote=True)


def warn(*a):
    print('  [warn]', *a, file=sys.stderr)


# ----------------------------------------------------------------------------- package
class Package:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.names = set(self.z.namelist())
        self._x, self._r = {}, {}

    def xml(self, part):
        if part not in self._x:
            self._x[part] = etree.fromstring(self.z.read(part))
        return self._x[part]

    def read(self, part):
        return self.z.read(part)

    def rels(self, part):
        if part in self._r:
            return self._r[part]
        d, b = posixpath.split(part)
        rp = posixpath.join(d, '_rels', b + '.rels')
        out = {}
        if rp in self.names:
            for r in etree.fromstring(self.z.read(rp)):
                tgt, mode = r.get('Target'), r.get('TargetMode')
                if mode != 'External':
                    tgt = tgt[1:] if tgt.startswith('/') else posixpath.normpath(posixpath.join(d, tgt))
                out[r.get('Id')] = (r.get('Type').rsplit('/', 1)[-1], tgt, mode)
        self._r[part] = out
        return out

    def rel_of_type(self, part, typ):
        for v in self.rels(part).values():
            if v[0] == typ:
                return v[1]
        return None


# ----------------------------------------------------------------------------- colours
def s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def l2s(c):
    c = min(1.0, max(0.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def clamp01(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v


class RGBA:
    __slots__ = ('r', 'g', 'b', 'a')

    def __init__(self, r, g, b, a=1.0):
        self.r, self.g, self.b, self.a = r, g, b, a

    def copy(self):
        return RGBA(self.r, self.g, self.b, self.a)

    def hex(self):
        return '#%02x%02x%02x' % tuple(int(round(clamp01(v) * 255)) for v in (self.r, self.g, self.b))

    def css(self):
        if self.a >= 0.999:
            return self.hex()
        return 'rgba(%d,%d,%d,%s)' % (tuple(int(round(clamp01(v) * 255)) for v in (self.r, self.g, self.b)) + (f2(round(self.a, 3)),))

    def tup(self):
        return tuple(int(round(clamp01(v) * 255)) for v in (self.r, self.g, self.b))


def hexrgb(h):
    h = (h or '000000').strip()
    if len(h) != 6:
        h = '000000'
    return RGBA(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


COLOR_TAGS = ('srgbClr', 'schemeClr', 'sysClr', 'prstClr', 'scrgbClr', 'hslClr')


def preset_color(name):
    n = name
    for a, b in (('dk', 'dark'), ('lt', 'light'), ('med', 'medium')):
        if n.startswith(a) and len(n) > len(a) and n[len(a)].isupper():
            n = b + n[len(a):]
            break
    try:
        r, g, b = ImageColor.getrgb(n.lower())[:3]
        return RGBA(r / 255, g / 255, b / 255)
    except Exception:
        return RGBA(0, 0, 0)


def apply_mods(c, el):
    """apply DrawingML colour transforms (children of a colour element)"""
    for m in el:
        t = ln(m)
        v = m.get('val')
        if v is None:
            if t == 'comp':
                h, l, s = colorsys.rgb_to_hls(c.r, c.g, c.b)
                c.r, c.g, c.b = colorsys.hls_to_rgb((h + 0.5) % 1, l, s)
            elif t == 'inv':
                c.r, c.g, c.b = 1 - c.r, 1 - c.g, 1 - c.b
            elif t == 'gray':
                y = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b
                c.r = c.g = c.b = y
            continue
        f = int(v) / 100000.0
        if t == 'alpha':
            c.a = f
        elif t == 'alphaMod':
            c.a *= f
        elif t == 'alphaOff':
            c.a = clamp01(c.a + f)
        elif t in ('lumMod', 'lumOff', 'lum', 'satMod', 'satOff', 'sat', 'hueMod', 'hueOff', 'hue'):
            h, l, s = colorsys.rgb_to_hls(c.r, c.g, c.b)
            if t == 'lumMod':
                l *= f
            elif t == 'lumOff':
                l += f
            elif t == 'lum':
                l = f
            elif t == 'satMod':
                s *= f
            elif t == 'satOff':
                s += f
            elif t == 'sat':
                s = f
            elif t == 'hueMod':
                h = (h * f) % 1
            elif t == 'hueOff':
                h = (h + int(v) / 60000.0 / 360.0) % 1
            elif t == 'hue':
                h = (int(v) / 60000.0 / 360.0) % 1
            c.r, c.g, c.b = colorsys.hls_to_rgb(h, clamp01(l), clamp01(s))
        elif t == 'tint':
            c.r, c.g, c.b = (l2s(1 - (1 - s2l(x)) * f) for x in (c.r, c.g, c.b))
        elif t == 'shade':
            c.r, c.g, c.b = (l2s(s2l(x) * f) for x in (c.r, c.g, c.b))
        elif t in ('red', 'green', 'blue'):
            setattr(c, t[0], clamp01(l2s(f)))
        elif t in ('redMod', 'greenMod', 'blueMod'):
            setattr(c, t[0], clamp01(l2s(s2l(getattr(c, t[0])) * f)))
        elif t in ('redOff', 'greenOff', 'blueOff'):
            setattr(c, t[0], clamp01(l2s(s2l(getattr(c, t[0])) + f)))
    return c


# ----------------------------------------------------------------------------- theme
class Theme:
    def __init__(self, root):
        self.colors = {}
        cs = root.find('.//a:clrScheme', NS)
        if cs is not None:
            for c in cs:
                if len(c):
                    ch = c[0]
                    if ln(ch) == 'srgbClr':
                        self.colors[ln(c)] = ch.get('val')
                    elif ln(ch) == 'sysClr':
                        self.colors[ln(c)] = ch.get('lastClr') or ('000000' if ch.get('val') == 'windowText' else 'FFFFFF')
        fs = root.find('.//a:fontScheme', NS)
        self.fonts = {}
        if fs is not None:
            for k, tag in (('mj', 'majorFont'), ('mn', 'minorFont')):
                f = fs.find('a:' + tag, NS)
                if f is not None:
                    for s in ('latin', 'ea', 'cs'):
                        e = f.find('a:' + s, NS)
                        self.fonts['+%s-%s' % (k, s[:2] if s != 'latin' else 'lt')] = e.get('typeface') if e is not None else ''
        fmt = root.find('.//a:fmtScheme', NS)

        def lst(tag):
            e = fmt.find('a:' + tag, NS) if fmt is not None else None
            return list(e) if e is not None else []
        self.fill_styles = lst('fillStyleLst')
        self.ln_styles = lst('lnStyleLst')
        self.effect_styles = lst('effectStyleLst')
        self.bg_styles = lst('bgFillStyleLst')


# ----------------------------------------------------------------------------- fonts
SEGOE = '"Segoe UI","Segoe UI Web (West European)","Segoe Fallback","Helvetica Neue",Helvetica,Arial,sans-serif'
FONT_STACKS = {
    'segoe ui': (SEGOE, None),
    'segoe ui semibold': ('"Segoe UI Semibold",' + SEGOE, 600),
    'segoe ui bold': (SEGOE, 700),
    'segoe ui light': ('"Segoe UI Light",' + SEGOE, 300),
    'segoe ui semilight': ('"Segoe UI Semilight",' + SEGOE, 350),
    'segoe ui black': ('"Segoe UI Black",' + SEGOE, 900),
    'segoe sans display': ('"Segoe Sans Display","Segoe UI Variable Display",' + SEGOE, None),
    'segoe sans display semibold': ('"Segoe Sans Display Semibold","Segoe Sans Display","Segoe UI Variable Display","Segoe UI Semibold",' + SEGOE, 600),
    'segoe sans text': ('"Segoe Sans Text","Segoe UI Variable Text",' + SEGOE, None),
    'segoe sans text semibold': ('"Segoe Sans Text Semibold","Segoe Sans Text","Segoe UI Semibold",' + SEGOE, 600),
    'segoe ui variable display': ('"Segoe UI Variable Display",' + SEGOE, None),
    'segoe ui emoji': ('"Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",' + SEGOE, None),
    'segoe ui symbol': ('"Segoe UI Symbol",' + SEGOE, None),
    'consolas': ('Consolas,"Consolas Fallback","Cascadia Mono",Menlo,Monaco,"Liberation Mono","Courier New",monospace', None),
    'cascadia code': ('"Cascadia Code",Consolas,Menlo,monospace', None),
    'courier new': ('"Courier New",Courier,"Liberation Mono",monospace', None),
    'arial': ('Arial,Helvetica,"Liberation Sans",sans-serif', None),
    'calibri': ('Calibri,Carlito,"Segoe UI",Arial,sans-serif', None),
    'calibri light': ('"Calibri Light",Calibri,Carlito,sans-serif', 300),
    'times new roman': ('"Times New Roman",Times,"Liberation Serif",serif', None),
    'wingdings': (SEGOE, None),
}
# PowerPoint "single" line pitch as a multiple of the font size (win ascent + descent)
LINE_FACTORS = {'segoe': 1.33, 'consolas': 1.17, 'cascadia': 1.17, 'arial': 1.15, 'calibri': 1.22,
                'courier': 1.13, 'times': 1.15}
_font_classes = {}


def font_class(face):
    key = (face or 'segoe ui').strip().lower()
    if key not in FONT_STACKS:
        # unknown face: put it first, fall back to Segoe stack
        FONT_STACKS[key] = ('"%s",%s' % (face.replace('"', ''), SEGOE), None)
    if key not in _font_classes:
        _font_classes[key] = 'f%d' % len(_font_classes)
    return _font_classes[key], FONT_STACKS[key][1]


def font_css():
    return ''.join('.%s{font-family:%s}' % (cls, FONT_STACKS[k][0]) for k, cls in _font_classes.items())


def line_factor(face):
    k = (face or '').lower()
    for name, f in LINE_FACTORS.items():
        if name in k:
            return f
    return 1.2


WINGDINGS = {0xA7: '\u25aa', 0xD8: '\u27a2', 0xFC: '\u2714', 0x71: '\u274f', 0x76: '\u2756', 0x6E: '\u25a0',
             0x6C: '\u25cf', 0x6F: '\u25cb', 0xA8: '\u25fb', 0x77: '\u25c6', 0xE0: '\u2794', 0xE8: '\u2794',
             0xF0: '\u21e8', 0x9F: '\u2022', 0x3E: '\u2713', 0xFB: '\u2716', 0x4A: '\u263a', 0x7C: '\u2756'}


def map_symbol_char(ch, face):
    if not ch:
        return '\u2022'
    o = ord(ch[0])
    f = (face or '').lower()
    if 0xF000 <= o <= 0xF0FF:
        o -= 0xF000
        if 'wingdings' in f or 'symbol' in f or not f:
            return WINGDINGS.get(o, '\u2022')
        return chr(o)
    if 'wingdings' in f:
        return WINGDINGS.get(o, '\u2022')
    if 'symbol' in f and o == 0xB7:
        return '\u2022'
    return ch


# ----------------------------------------------------------------------------- guide formulas (custGeom)
def eval_guides(gd_list, av_list, w, h, extra_adj=None):
    v = {'l': 0, 't': 0, 'r': w, 'b': h, 'w': w, 'h': h, 'hc': w / 2, 'vc': h / 2,
         'ss': min(w, h), 'ls': max(w, h), 'cd2': 10800000, 'cd4': 5400000, 'cd8': 2700000,
         '3cd4': 16200000, '3cd8': 8100000, '5cd8': 13500000, '7cd8': 18900000}
    for n in (2, 3, 4, 5, 6, 8, 10, 12, 32):
        v['wd%d' % n] = w / n
        v['hd%d' % n] = h / n
    for n in (2, 4, 6, 8, 16, 32):
        v['ssd%d' % n] = min(w, h) / n

    def val(x):
        if x in v:
            return v[x]
        try:
            return float(x)
        except ValueError:
            return 0.0

    def run(f):
        p = f.split()
        op, a = p[0], [val(x) for x in p[1:]]
        ang = lambda d: math.radians(d / 60000.0)
        if op == '*/': return a[0] * a[1] / a[2] if a[2] else 0
        if op == '+-': return a[0] + a[1] - a[2]
        if op == '+/': return (a[0] + a[1]) / a[2] if a[2] else 0
        if op == '?:': return a[1] if a[0] > 0 else a[2]
        if op == 'abs': return abs(a[0])
        if op == 'at2': return math.degrees(math.atan2(a[1], a[0])) * 60000
        if op == 'cat2': return a[0] * math.cos(math.atan2(a[2], a[1]))
        if op == 'sat2': return a[0] * math.sin(math.atan2(a[2], a[1]))
        if op == 'cos': return a[0] * math.cos(ang(a[1]))
        if op == 'sin': return a[0] * math.sin(ang(a[1]))
        if op == 'tan': return a[0] * math.tan(ang(a[1]))
        if op == 'max': return max(a[0], a[1])
        if op == 'min': return min(a[0], a[1])
        if op == 'mod': return math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
        if op == 'pin': return a[0] if a[1] < a[0] else a[2] if a[1] > a[2] else a[1]
        if op == 'sqrt': return math.sqrt(max(0, a[0]))
        if op == 'val': return a[0]
        return 0.0
    for lst in (av_list, gd_list):
        if lst is None:
            continue
        for g in lst:
            try:
                v[g.get('name')] = run(g.get('fmla'))
            except Exception:
                v[g.get('name')] = 0.0
    if extra_adj:
        v.update(extra_adj)
    return v, val


# ----------------------------------------------------------------------------- path builder
class PB:
    def __init__(self):
        self.d = []
        self.x = self.y = 0.0

    def M(self, x, y):
        self.d.append('M%s %s' % (f2(x), f2(y)))
        self.x, self.y = x, y
        return self

    def L(self, x, y):
        self.d.append('L%s %s' % (f2(x), f2(y)))
        self.x, self.y = x, y
        return self

    def C(self, x1, y1, x2, y2, x, y):
        self.d.append('C%s %s %s %s %s %s' % tuple(f2(t) for t in (x1, y1, x2, y2, x, y)))
        self.x, self.y = x, y
        return self

    def Qd(self, x1, y1, x, y):
        self.d.append('Q%s %s %s %s' % tuple(f2(t) for t in (x1, y1, x, y)))
        self.x, self.y = x, y
        return self

    def Z(self):
        self.d.append('Z')
        return self

    def arc(self, wr, hr, st, sw):
        """DrawingML arcTo: radii, start angle and sweep in degrees (clockwise, y down)"""
        if abs(sw) < 1e-9:
            return self
        if abs(sw) >= 359.99:
            self.arc(wr, hr, st, sw / 2)
            return self.arc(wr, hr, st + sw / 2, sw / 2)
        a0 = math.radians(st)
        cx, cy = self.x - wr * math.cos(a0), self.y - hr * math.sin(a0)
        a1 = math.radians(st + sw)
        ex, ey = cx + wr * math.cos(a1), cy + hr * math.sin(a1)
        if wr < 1e-6 or hr < 1e-6:
            return self.L(ex, ey)
        self.d.append('A%s %s 0 %d %d %s %s' % (f2(wr), f2(hr), 1 if abs(sw) > 180 else 0, 1 if sw > 0 else 0, f2(ex), f2(ey)))
        self.x, self.y = ex, ey
        return self

    def s(self):
        return ''.join(self.d)


def ellipse_path(w, h, x0=0.0, y0=0.0):
    p = PB().M(x0, y0 + h / 2)
    p.arc(w / 2, h / 2, 180, 180).arc(w / 2, h / 2, 0, 180).Z()
    return p.s()


def adj(av, name, default):
    return av.get(name, default)


def preset_geometry(prst, w, h, av):
    """returns (list of (d, fill, stroke)), text rect (l,t,r,b) in px of the shape box"""
    ss = min(w, h)
    tr = (0, 0, w, h)
    P = []
    if prst in ('rect', 'flowChartProcess', 'actionButtonBlank', 'textBox', None, ''):
        P.append(('M0 0H%sV%sH0Z' % (f2(w), f2(h)), True, True))
    elif prst in ('roundRect', 'flowChartAlternateProcess'):
        a = min(50000, max(0, adj(av, 'adj', 16667 if prst == 'roundRect' else 16667)))
        r = ss * a / 100000
        p = PB().M(0, r).arc(r, r, 180, 90).L(w - r, 0).arc(r, r, 270, 90).L(w, h - r).arc(r, r, 0, 90).L(r, h).arc(r, r, 90, 90).Z()
        P.append((p.s(), True, True))
        il = r * 0.29289
        tr = (il, il, w - il, h - il)
    elif prst == 'round2SameRect':
        a1 = min(50000, max(0, adj(av, 'adj1', 16667)))
        a2 = min(50000, max(0, adj(av, 'adj2', 0)))
        r1, r2 = ss * a1 / 100000, ss * a2 / 100000
        p = PB().M(r1, 0).L(w - r1, 0).arc(r1, r1, 270, 90).L(w, h - r2).arc(r2, r2, 0, 90).L(r2, h).arc(r2, r2, 90, 90).L(0, r1).arc(r1, r1, 180, 90).Z()
        P.append((p.s(), True, True))
        il = max(r1, r2) * 0.29289
        tr = (il, r1 * 0.29289, w - il, h - r2 * 0.29289)
    elif prst == 'round1Rect':
        r = ss * min(50000, max(0, adj(av, 'adj', 16667))) / 100000
        p = PB().M(0, 0).L(w - r, 0).arc(r, r, 270, 90).L(w, h).L(0, h).Z()
        P.append((p.s(), True, True))
    elif prst == 'round2DiagRect':
        r1 = ss * adj(av, 'adj1', 16667) / 100000
        r2 = ss * adj(av, 'adj2', 0) / 100000
        p = PB().M(r1, 0).L(w - r2, 0).arc(r2, r2, 270, 90).L(w, h - r1).arc(r1, r1, 0, 90).L(r2, h).arc(r2, r2, 90, 90).L(0, r1).arc(r1, r1, 180, 90).Z()
        P.append((p.s(), True, True))
    elif prst == 'snip1Rect':
        r = ss * adj(av, 'adj', 16667) / 100000
        P.append(('M0 0H%sL%s %sV%sH0Z' % (f2(w - r), f2(w), f2(r), f2(h)), True, True))
    elif prst == 'snip2SameRect':
        r1 = ss * adj(av, 'adj1', 16667) / 100000
        r2 = ss * adj(av, 'adj2', 0) / 100000
        p = PB().M(r1, 0).L(w - r1, 0).L(w, r1).L(w, h - r2).L(w - r2, h).L(r2, h).L(0, h - r2).L(0, r1).Z()
        P.append((p.s(), True, True))
    elif prst in ('ellipse', 'flowChartConnector'):
        P.append((ellipse_path(w, h), True, True))
        tr = (w * 0.14645, h * 0.14645, w * 0.85355, h * 0.85355)
    elif prst in ('line', 'straightConnector1'):
        P.append(('M0 0L%s %s' % (f2(w), f2(h)), False, True))
    elif prst == 'bentConnector2':
        P.append(('M0 0H%sV%s' % (f2(w), f2(h)), False, True))
    elif prst == 'bentConnector3':
        x1 = w * adj(av, 'adj1', 50000) / 100000
        P.append(('M0 0H%sV%sH%s' % (f2(x1), f2(h), f2(w)), False, True))
    elif prst == 'bentConnector4':
        x1 = w * adj(av, 'adj1', 50000) / 100000
        y2 = h * adj(av, 'adj2', 50000) / 100000
        P.append(('M0 0H%sV%sH%sV%s' % (f2(x1), f2(y2), f2(w), f2(h)), False, True))
    elif prst in ('curvedConnector3',):
        x2 = w * adj(av, 'adj1', 50000) / 100000
        p = PB().M(0, 0).C(x2 / 2, 0, x2, h / 4, x2, h / 2).C(x2, 3 * h / 4, (w + x2) / 2, h, w, h)
        P.append((p.s(), False, True))
    elif prst == 'curvedConnector2':
        P.append((PB().M(0, 0).C(w / 2, 0, w, h / 2, w, h).s(), False, True))
    elif prst == 'triangle':
        x = w * adj(av, 'adj', 50000) / 100000
        P.append(('M%s 0L%s %sH0Z' % (f2(x), f2(w), f2(h)), True, True))
        tr = (x / 2, h / 2, (x + w) / 2, h)
    elif prst == 'rtTriangle':
        P.append(('M0 0V%sH%sZ' % (f2(h), f2(w)), True, True))
    elif prst in ('diamond', 'flowChartDecision'):
        P.append(('M%s 0L%s %sL%s %sL0 %sZ' % (f2(w / 2), f2(w), f2(h / 2), f2(w / 2), f2(h), f2(h / 2)), True, True))
        tr = (w / 4, h / 4, 3 * w / 4, 3 * h / 4)
    elif prst in ('parallelogram', 'flowChartInputOutput'):
        x2 = ss * adj(av, 'adj', 25000) / 100000 if prst == 'parallelogram' else w / 5
        P.append(('M0 %sL%s 0H%sL%s %sZ' % (f2(h), f2(x2), f2(w), f2(w - x2), f2(h)), True, True))
        tr = (x2 / 2, 0, w - x2 / 2, h)
    elif prst == 'trapezoid':
        x2 = ss * adj(av, 'adj', 25000) / 100000
        P.append(('M0 %sL%s 0H%sL%s %sZ' % (f2(h), f2(x2), f2(w - x2), f2(w), f2(h)), True, True))
    elif prst == 'hexagon':
        x1 = ss * adj(av, 'adj', 25000) / 100000
        P.append(('M0 %sL%s 0H%sL%s %sL%s %sH%sZ' % (f2(h / 2), f2(x1), f2(w - x1), f2(w), f2(h / 2), f2(w - x1), f2(h), f2(x1)), True, True))
    elif prst == 'octagon':
        x1 = ss * adj(av, 'adj', 29289) / 100000
        P.append(('M0 %sL%s 0H%sL%s %sV%sL%s %sH%sL0 %sZ' % (f2(x1), f2(x1), f2(w - x1), f2(w), f2(x1), f2(h - x1), f2(w - x1), f2(h), f2(x1), f2(h - x1)), True, True))
    elif prst == 'pentagon':
        pts = [(w / 2, 0), (w, h * 0.382), (w * 0.809, h), (w * 0.191, h), (0, h * 0.382)]
        P.append(('M' + 'L'.join('%s %s' % (f2(x), f2(y)) for x, y in pts) + 'Z', True, True))
    elif prst == 'homePlate':
        x1 = w - ss * adj(av, 'adj', 50000) / 100000
        P.append(('M0 0H%sL%s %sL%s %sH0Z' % (f2(x1), f2(w), f2(h / 2), f2(x1), f2(h)), True, True))
        tr = (0, 0, (x1 + w) / 2, h)
    elif prst == 'chevron':
        x1 = ss * adj(av, 'adj', 50000) / 100000
        P.append(('M0 0H%sL%s %sL%s %sH0L%s %sZ' % (f2(w - x1), f2(w), f2(h / 2), f2(w - x1), f2(h), f2(x1), f2(h / 2)), True, True))
        tr = (x1, 0, w - x1, h)
    elif prst in ('rightArrow', 'leftArrow', 'upArrow', 'downArrow', 'leftRightArrow', 'upDownArrow'):
        a1 = adj(av, 'adj1', 50000)
        a2 = adj(av, 'adj2', 50000)
        if prst in ('rightArrow', 'leftArrow', 'leftRightArrow'):
            dy = h * a1 / 200000
            y1, y2 = h / 2 - dy, h / 2 + dy
            hl = ss * a2 / 100000
            if prst == 'rightArrow':
                x1 = w - hl
                d = 'M0 %sH%sV0L%s %sL%s %sV%sH0Z' % (f2(y1), f2(x1), f2(w), f2(h / 2), f2(x1), f2(h), f2(y2))
            elif prst == 'leftArrow':
                x1 = hl
                d = 'M0 %sL%s 0V%sH%sV%sH%sV%sZ' % (f2(h / 2), f2(x1), f2(y1), f2(w), f2(y2), f2(x1), f2(h))
            else:
                x1, x2 = hl, w - hl
                d = 'M0 %sL%s 0V%sH%sV0L%s %sL%s %sV%sH%sV%sZ' % (f2(h / 2), f2(x1), f2(y1), f2(x2), f2(w), f2(h / 2), f2(x2), f2(h), f2(y2), f2(x1), f2(h))
        else:
            dx = w * a1 / 200000
            x1, x2 = w / 2 - dx, w / 2 + dx
            hl = ss * a2 / 100000
            if prst == 'downArrow':
                y1 = h - hl
                d = 'M%s 0H%sV%sH%sL%s %sL0 %sH%sZ' % (f2(x1), f2(x2), f2(y1), f2(w), f2(w / 2), f2(h), f2(y1), f2(x1))
            elif prst == 'upArrow':
                y1 = hl
                d = 'M%s 0L%s %sH%sV%sH%sV%sH0Z' % (f2(w / 2), f2(w), f2(y1), f2(x2), f2(h), f2(x1), f2(y1))
            else:
                y1, y2 = hl, h - hl
                d = 'M%s 0L%s %sH%sV%sH%sL%s %sL0 %sH%sV%sH0Z' % (f2(w / 2), f2(w), f2(y1), f2(x2), f2(y2), f2(w), f2(w / 2), f2(h), f2(y2), f2(x1), f2(y1))
        P.append((d, True, True))
    elif prst == 'plus':
        x1 = ss * adj(av, 'adj', 25000) / 100000
        P.append(('M%s 0H%sV%sH%sV%sH%sV%sH%sV%sH0V%sH%sZ' % (f2(x1), f2(w - x1), f2(x1), f2(w), f2(h - x1), f2(w - x1), f2(h), f2(x1), f2(h - x1), f2(x1), f2(x1)), True, True))
    elif prst in ('donut', 'frame'):
        if prst == 'donut':
            t = ss * adj(av, 'adj', 25000) / 100000
            d = ellipse_path(w, h) + ellipse_path(w - 2 * t, h - 2 * t, t, t)
        else:
            t = ss * adj(av, 'adj1', 12500) / 100000
            d = 'M0 0H%sV%sH0Z' % (f2(w), f2(h)) + 'M%s %sV%sH%sV%sZ' % (f2(t), f2(t), f2(h - t), f2(w - t), f2(t))
        P.append((d, True, True))
    elif prst in ('rightBrace', 'leftBrace'):
        a2 = min(100000, max(0, adj(av, 'adj2', 50000)))
        q2 = min(100000 - a2, a2)
        a1 = min(q2 / 2 * h / ss if ss else 0, max(0, adj(av, 'adj1', 8333)))
        y1 = ss * a1 / 100000
        y3 = h * a2 / 100000
        p = PB().M(0, 0).arc(w / 2, y1, 270, 90).L(w / 2, y3 - y1).arc(w / 2, y1, 180, -90).arc(w / 2, y1, 270, -90).L(w / 2, h - y1).arc(w / 2, y1, 0, 90)
        d = p.s()
        if prst == 'leftBrace':
            d = mirror_path_x(d, w)
        P.append((d + 'Z', True, False))
        P.append((d, False, True))
    elif prst in ('rightBracket', 'leftBracket'):
        y1 = ss * adj(av, 'adj', 8333) / 100000
        p = PB().M(0, 0).arc(w, y1, 270, 90).L(w, h - y1).arc(w, y1, 0, 90)
        d = p.s()
        if prst == 'leftBracket':
            d = mirror_path_x(d, w)
        P.append((d + 'Z', True, False))
        P.append((d, False, True))
    elif prst in ('arc', 'pie', 'chord', 'blockArc'):
        st = adj(av, 'adj1', 16200000 if prst == 'arc' else 0) / 60000.0
        en = adj(av, 'adj2', 0 if prst == 'arc' else 16200000) / 60000.0
        sw = (en - st) % 360 or 360
        rx, ry = w / 2, h / 2
        sx, sy = rx + rx * math.cos(math.radians(st)), ry + ry * math.sin(math.radians(st))
        p = PB().M(sx, sy).arc(rx, ry, st, sw)
        if prst == 'arc':
            P.append((p.s() + 'L%s %sZ' % (f2(rx), f2(ry)), True, False))
            P.append((p.s(), False, True))
        elif prst == 'pie':
            P.append((p.s() + 'L%s %sZ' % (f2(rx), f2(ry)), True, True))
        else:
            P.append((p.s() + 'Z', True, True))
    elif prst in ('star5', 'star4', 'star6', 'star8'):
        n = int(prst[4:])
        inner = {4: 0.38, 5: 0.38, 6: 0.5, 8: 0.6}[n]
        pts = []
        for i in range(2 * n):
            ang = -math.pi / 2 + i * math.pi / n
            rr = 1 if i % 2 == 0 else inner
            pts.append((w / 2 + w / 2 * rr * math.cos(ang), h / 2 + h / 2 * rr * math.sin(ang)))
        P.append(('M' + 'L'.join('%s %s' % (f2(x), f2(y)) for x, y in pts) + 'Z', True, True))
    elif prst == 'flowChartTerminator':
        r = min(w * 3475 / 21600, h / 2)
        p = PB().M(r, 0).L(w - r, 0).arc(r, h / 2, 270, 180).L(r, h).arc(r, h / 2, 90, 180).Z()
        P.append((p.s(), True, True))
    elif prst in ('wedgeRectCallout', 'wedgeRoundRectCallout', 'wedgeEllipseCallout'):
        dx = w * adj(av, 'adj1', -20833) / 100000
        dy = h * adj(av, 'adj2', 62500) / 100000
        tx, ty = w / 2 + dx, h / 2 + dy
        if prst == 'wedgeEllipseCallout':
            body = ellipse_path(w, h)
        elif prst == 'wedgeRoundRectCallout':
            r = ss * 16667 / 100000
            body = PB().M(0, r).arc(r, r, 180, 90).L(w - r, 0).arc(r, r, 270, 90).L(w, h - r).arc(r, r, 0, 90).L(r, h).arc(r, r, 90, 90).Z().s()
        else:
            body = 'M0 0H%sV%sH0Z' % (f2(w), f2(h))
        # tail as a triangle from two points on the nearest edge to the tip
        if abs(dy) * w >= abs(dx) * h:
            yb = h if dy > 0 else 0
            xa, xb = w * (0.25 if dx < 0 else 0.583), w * (0.417 if dx < 0 else 0.75)
            tail = 'M%s %sL%s %sL%s %sZ' % (f2(xa), f2(yb), f2(tx), f2(ty), f2(xb), f2(yb))
        else:
            xb = w if dx > 0 else 0
            ya, yb2 = h * 0.583, h * 0.75
            tail = 'M%s %sL%s %sL%s %sZ' % (f2(xb), f2(ya), f2(tx), f2(ty), f2(xb), f2(yb2))
        P.append((body + tail, True, True))
    elif prst in ('cloud', 'cloudCallout', 'teardrop', 'heart', 'sun', 'moon', 'smileyFace', 'noSmoking', 'can', 'cube', 'bevel', 'foldedCorner', 'plaque', 'flowChartDocument', 'flowChartMultidocument', 'flowChartPredefinedProcess', 'flowChartManualInput', 'flowChartPunchedCard', 'wave', 'doubleWave', 'ribbon', 'ribbon2', 'verticalScroll', 'horizontalScroll'):
        if prst in ('cloud', 'cloudCallout', 'sun', 'smileyFace', 'noSmoking', 'teardrop', 'heart', 'moon'):
            P.append((ellipse_path(w, h), True, True))
        else:
            P.append(('M0 0H%sV%sH0Z' % (f2(w), f2(h)), True, True))
        warn('approximated preset geometry', prst)
    else:
        P.append(('M0 0H%sV%sH0Z' % (f2(w), f2(h)), True, True))
        warn('unsupported preset geometry', prst, '-> rect')
    return P, tr


def mirror_path_x(d, w):
    """mirror an absolute SVG path (M/L/C/Q/A/H/V commands) horizontally within width w"""
    out = []
    for cmd, args in re.findall(r'([MLCQAHVZ])([^MLCQAHVZ]*)', d):
        nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e-?\d+)?', args)]
        if cmd in 'MLCQ':
            nums = [w - v if i % 2 == 0 else v for i, v in enumerate(nums)]
        elif cmd == 'H':
            nums = [w - v for v in nums]
        elif cmd == 'A':
            nums[4] = 1 - nums[4]
            nums[5] = w - nums[5]
        out.append(cmd + ' '.join(f2(v) if not (cmd == 'A' and i in (2, 3, 4)) else str(int(v)) for i, v in enumerate(nums)))
    return ''.join(out)


DASHES = {'dash': [4, 3], 'dot': [1, 3], 'lgDash': [8, 3], 'dashDot': [4, 3, 1, 3], 'lgDashDot': [8, 3, 1, 3],
          'lgDashDotDot': [8, 3, 1, 3, 1, 3], 'sysDash': [3, 1], 'sysDot': [1, 1], 'sysDashDot': [3, 1, 1, 1],
          'sysDashDotDot': [3, 1, 1, 1, 1, 1]}
ARROW_SIZE = {'sm': 2.0, 'med': 3.0, 'lg': 5.0}


# ----------------------------------------------------------------------------- assets
class Assets:
    """collects image/media requests, then encodes web-friendly files"""

    def __init__(self, pkg, outdir, media_dir=None, scale=1.5, max_px=2600):
        self.pkg, self.out, self.media_dir = pkg, outdir, media_dir
        self.scale, self.max_px = scale, max_px
        self.req = {}  # key -> dict
        self.urls = {}
        os.makedirs(os.path.join(outdir, 'assets', 'img'), exist_ok=True)
        os.makedirs(os.path.join(outdir, 'assets', 'media'), exist_ok=True)

    def image(self, part, crop=None, disp=(0, 0), effects=None, prefer_svg=None):
        crop = tuple(round(c, 5) for c in crop) if crop else (0, 0, 0, 0)
        key = hashlib.sha1(repr((part, crop, effects, prefer_svg)).encode()).hexdigest()[:12]
        r = self.req.setdefault(key, {'part': part, 'crop': crop, 'w': 0, 'h': 0, 'effects': effects, 'svg': prefer_svg})
        r['w'] = max(r['w'], disp[0])
        r['h'] = max(r['h'], disp[1])
        return key

    def url(self, key):
        return self.urls.get(key, '')

    def media(self, part):
        base = posixpath.basename(part)
        stem = os.path.splitext(base)[0]
        dst_name = stem + '.mp4'
        dst = os.path.join(self.out, 'assets', 'media', dst_name)
        if not os.path.exists(dst):
            src = os.path.join(self.media_dir, stem + '.mp4') if self.media_dir else None
            if src and os.path.exists(src):
                shutil.copyfile(src, dst)
            else:
                with open(dst, 'wb') as fh:
                    fh.write(self.pkg.read(part))
        return 'assets/media/' + dst_name

    def has_transcoded(self, part):
        stem = os.path.splitext(posixpath.basename(part))[0]
        return bool(self.media_dir and os.path.exists(os.path.join(self.media_dir, stem + '.mp4')))

    def finalize(self):
        emf_parts = sorted({r['part'] for r in self.req.values() if r['part'].lower().endswith(('.emf', '.wmf')) and not r['svg']})
        emf_svgs = convert_emf(self.pkg, emf_parts) if emf_parts else {}
        total = 0
        for key, r in self.req.items():
            part = r['part']
            stem = re.sub(r'[^a-zA-Z0-9_-]', '', os.path.splitext(posixpath.basename(part))[0])
            try:
                if r['svg']:
                    name = '%s-%s.svg' % (stem, key[:6])
                    data = self.pkg.read(r['svg'])
                    with open(os.path.join(self.out, 'assets', 'img', name), 'wb') as fh:
                        fh.write(data)
                elif part.lower().endswith(('.emf', '.wmf')):
                    name = '%s-%s.svg' % (stem, key[:6])
                    data = emf_svgs.get(part)
                    if data is None:
                        warn('could not convert', part)
                        continue
                    with open(os.path.join(self.out, 'assets', 'img', name), 'wb') as fh:
                        fh.write(data)
                else:
                    name, data = self.encode_raster(key, r, stem)
                total += len(data)
                self.urls[key] = 'assets/img/' + name
            except Exception as ex:
                warn('image failed', part, ex)
        return total

    def encode_raster(self, key, r, stem):
        raw = self.pkg.read(r['part'])
        im = Image.open(io.BytesIO(raw))
        try:
            im.seek(0)
        except Exception:
            pass
        im = ImageOps.exif_transpose(im) if hasattr(ImageOps, 'exif_transpose') else im
        has_alpha = im.mode in ('RGBA', 'LA', 'PA') or (im.mode == 'P' and 'transparency' in im.info)
        im = im.convert('RGBA' if has_alpha else 'RGB')
        W, H = im.size
        l, t, rr, b = r['crop']
        if any(r['crop']):
            box = [l * W, t * H, W - rr * W, H - b * H]
            if l < 0 or t < 0 or rr < 0 or b < 0:
                # negative crop = padding: paste onto a transparent canvas
                cw, ch = int(round(box[2] - box[0])), int(round(box[3] - box[1]))
                canvas = Image.new('RGBA', (max(1, cw), max(1, ch)), (0, 0, 0, 0))
                canvas.paste(im.convert('RGBA'), (int(round(-box[0])), int(round(-box[1]))))
                im = canvas
                has_alpha = True
            else:
                im = im.crop(tuple(int(round(v)) for v in box))
        eff = dict(r['effects']) if r['effects'] else {}
        if eff:
            im = apply_blip_effects(im, eff)
            if eff.get('alpha') is not None:
                has_alpha = True
        tw, th = r['w'] * self.scale, r['h'] * self.scale
        cw, ch = im.size
        f = 1.0
        if tw > 0 and th > 0:
            f = min(1.0, max(tw / cw, th / ch))
        f = min(f, self.max_px / max(cw, ch))
        if f < 0.98:
            im = im.resize((max(1, int(round(cw * f))), max(1, int(round(ch * f)))), Image.LANCZOS)
        if has_alpha and im.mode == 'RGBA' and im.getextrema()[3][0] == 255:
            has_alpha = False
            im = im.convert('RGB')
        src_png = r['part'].lower().endswith(('.png', '.gif', '.bmp', '.tif', '.tiff'))
        buf = io.BytesIO()
        if src_png:
            lossy = io.BytesIO()
            im.save(lossy, 'WEBP', quality=88, method=6)
            lossless = io.BytesIO()
            if im.size[0] * im.size[1] <= 1600 * 1600:
                im.save(lossless, 'WEBP', lossless=True, method=6, quality=90)
            buf = lossless if lossless.tell() and lossless.tell() <= lossy.tell() * 1.25 else lossy
        else:
            im.save(buf, 'WEBP', quality=84, method=6)
        name = '%s-%s.webp' % (stem, key[:6])
        data = buf.getvalue()
        with open(os.path.join(self.out, 'assets', 'img', name), 'wb') as fh:
            fh.write(data)
        return name, data


def apply_blip_effects(im, eff):
    if eff.get('duotone'):
        c1, c2 = eff['duotone']
        alpha = im.getchannel('A') if im.mode == 'RGBA' else None
        g = ImageOps.grayscale(im.convert('RGB'))
        im = ImageOps.colorize(g, black=c1, white=c2)
        if alpha is not None:
            im = im.convert('RGBA')
            im.putalpha(alpha)
    if eff.get('gray'):
        alpha = im.getchannel('A') if im.mode == 'RGBA' else None
        im = ImageOps.grayscale(im.convert('RGB')).convert('RGB')
        if alpha is not None:
            im = im.convert('RGBA')
            im.putalpha(alpha)
    if eff.get('bright') or eff.get('contrast'):
        alpha = im.getchannel('A') if im.mode == 'RGBA' else None
        rgb = im.convert('RGB')
        if eff.get('bright'):
            rgb = ImageEnhance.Brightness(rgb).enhance(1 + eff['bright'])
        if eff.get('contrast'):
            rgb = ImageEnhance.Contrast(rgb).enhance(1 + eff['contrast'])
        im = rgb
        if alpha is not None:
            im = im.convert('RGBA')
            im.putalpha(alpha)
    if eff.get('alpha') is not None:
        im = im.convert('RGBA')
        a = im.getchannel('A').point(lambda v: int(v * eff['alpha']))
        im.putalpha(a)
    return im


def convert_emf(pkg, parts):
    """convert EMF/WMF parts to tightly cropped SVG with LibreOffice"""
    out = {}
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice:
        return out
    tmp = tempfile.mkdtemp(prefix='emf')
    files = []
    for i, p in enumerate(parts):
        fn = os.path.join(tmp, 'g%d%s' % (i, os.path.splitext(p)[1].lower()))
        with open(fn, 'wb') as fh:
            fh.write(pkg.read(p))
        files.append((p, fn))
    subprocess.run([soffice, '--headless', '--norestore', '--convert-to', 'svg', '--outdir', tmp] + [f for _, f in files],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    for p, fn in files:
        svgf = os.path.splitext(fn)[0] + '.svg'
        if not os.path.exists(svgf):
            continue
        s = open(svgf, encoding='utf8').read()
        m = re.search(r'<rect class="BoundingBox"[^>]*x="(-?\d+)" y="(-?\d+)" width="(\d+)" height="(\d+)"', s)
        if m:
            x, y, w, h = m.groups()
            s = re.sub(r'<svg([^>]*?) width="[^"]*" height="[^"]*" viewBox="[^"]*"',
                       lambda mm: '<svg%s viewBox="%s %s %s %s" preserveAspectRatio="none"' % (mm.group(1), x, y, w, h), s, count=1)
        s = re.sub(r'<!DOCTYPE[^>]*>', '', s)
        s = re.sub(r'(<svg[^>]*?) preserveAspectRatio="xMidYMid"', r'\1', s, count=1)
        out[p] = s.encode('utf8')
    shutil.rmtree(tmp, ignore_errors=True)
    return out


# ----------------------------------------------------------------------------- the converter
class SlideCtx:
    def __init__(self, deck, part):
        self.deck = deck
        pkg = deck.pkg
        self.part = part
        self.el = pkg.xml(part)
        self.layout_part = pkg.rel_of_type(part, 'slideLayout')
        self.layout = pkg.xml(self.layout_part)
        self.master_part = pkg.rel_of_type(self.layout_part, 'slideMaster')
        self.master = pkg.xml(self.master_part)
        self.theme = deck.theme_for(self.master_part)
        cm = self.master.find('p:clrMap', NS)
        self.clrmap = dict(cm.attrib) if cm is not None else {}
        for src in (self.layout, self.el):
            o = src.find('p:clrMapOvr/a:overrideClrMapping', NS)
            if o is not None:
                self.clrmap = dict(o.attrib)
        tx = self.master.find('p:txStyles', NS)
        self.styles = {
            'title': tx.find('p:titleStyle', NS) if tx is not None else None,
            'body': tx.find('p:bodyStyle', NS) if tx is not None else None,
            'other': tx.find('p:otherStyle', NS) if tx is not None else None,
        }
        self.default_style = deck.pres.find('p:defaultTextStyle', NS)
        self.layout_ph = self.collect_ph(self.layout)
        self.master_ph = self.collect_ph(self.master)

    @staticmethod
    def collect_ph(root):
        out = []
        tree = root.find('p:cSld/p:spTree', NS)
        if tree is None:
            return out
        for sp in tree.iter(Q('p:sp'), Q('p:pic')):
            ph = sp.find('./*/p:nvPr/p:ph', NS)
            if ph is not None:
                out.append((ph.get('type', 'obj'), ph.get('idx'), sp))
        return out

    # colours ---------------------------------------------------------------
    def color(self, el, ph=None):
        """el: colour element (srgbClr, schemeClr...)"""
        if el is None:
            return None
        t = ln(el)
        if t == 'srgbClr':
            c = hexrgb(el.get('val'))
        elif t == 'schemeClr':
            v = el.get('val')
            if v == 'phClr':
                c = ph.copy() if ph is not None else RGBA(0, 0, 0)
            else:
                name = self.clrmap.get(v, v)
                c = hexrgb(self.theme.colors.get(name, '000000'))
        elif t == 'sysClr':
            c = hexrgb(el.get('lastClr') or ('000000' if el.get('val') == 'windowText' else 'FFFFFF'))
        elif t == 'prstClr':
            c = preset_color(el.get('val'))
        elif t == 'scrgbClr':
            c = RGBA(l2s(int(el.get('r', 0)) / 100000), l2s(int(el.get('g', 0)) / 100000), l2s(int(el.get('b', 0)) / 100000))
        elif t == 'hslClr':
            r, g, b = colorsys.hls_to_rgb(int(el.get('hue', 0)) / 60000 / 360, int(el.get('lum', 0)) / 100000, int(el.get('sat', 0)) / 100000)
            c = RGBA(r, g, b)
        else:
            return None
        return apply_mods(c, el)

    def color_in(self, parent, ph=None):
        if parent is None:
            return None
        for ch in parent:
            if ln(ch) in COLOR_TAGS:
                return self.color(ch, ph)
        return None


class Deck:
    def __init__(self, path, outdir, media_dir=None, include_hidden=False):
        self.pkg = Package(path)
        self.out = outdir
        self.pres_part = 'ppt/presentation.xml'
        self.pres = self.pkg.xml(self.pres_part)
        sz = self.pres.find('p:sldSz', NS)
        self.cx, self.cy = int(sz.get('cx')), int(sz.get('cy'))
        self.H = 1080
        self.W = int(round(1080 * self.cx / self.cy))
        self.k = self.H / self.cy          # px per EMU
        self.pt = 12700 * self.k            # px per point
        self.include_hidden = include_hidden
        self._themes = {}
        rels = self.pkg.rels(self.pres_part)
        self.slide_parts = []
        for s in self.pres.findall('p:sldIdLst/p:sldId', NS):
            self.slide_parts.append(rels[s.get(Q('r:id'))][1])
        self.assets = Assets(self.pkg, outdir, media_dir)
        self.uid = 0

    def theme_for(self, master_part):
        tp = self.pkg.rel_of_type(master_part, 'theme')
        if tp not in self._themes:
            self._themes[tp] = Theme(self.pkg.xml(tp))
        return self._themes[tp]

    def nid(self, prefix='g'):
        self.uid += 1
        return '%s%d' % (prefix, self.uid)


# ---- AlternateContent handling
OK_REQ = {'p14', 'a14', 'p15', 'a16', 'asvg', 'adec', 'a15', 'p159', 'v', 'wps'}


def resolve_alt(el):
    """return the element(s) to use for an mc:AlternateContent"""
    for ch in el:
        if ln(ch) == 'Choice':
            req = set((ch.get('Requires') or '').split())
            if req <= OK_REQ:
                return list(ch)
        elif ln(ch) == 'Fallback':
            return list(ch)
    return []


def iter_tree(tree):
    for ch in tree:
        if not isinstance(ch.tag, str):
            continue
        if ln(ch) == 'AlternateContent':
            for c in resolve_alt(ch):
                yield c
        else:
            yield ch


# ----------------------------------------------------------------------------- shape building
class Builder:
    def __init__(self, deck, ctx, slide_index):
        self.deck, self.ctx, self.si = deck, ctx, slide_index
        self.k = deck.k
        self.pt = deck.pt
        self.defs_id = 0

    # --- placeholder chain -------------------------------------------------
    def ph_chain(self, sp, level):
        """for a shape at `level` ('slide','layout','master'), return (ph_type, layout_el, master_el)"""
        ph = sp.find('./*/p:nvPr/p:ph', NS)
        if ph is None:
            return None, None, None
        typ, idx = ph.get('type', 'obj'), ph.get('idx')
        lay = mas = None
        if level == 'slide':
            lay = self.match_ph(self.ctx.layout_ph, typ, idx)
            ltyp = typ
            if lay is not None:
                lph = lay.find('./*/p:nvPr/p:ph', NS)
                ltyp = lph.get('type', 'obj')
            mas = self.match_master(ltyp)
        elif level == 'layout':
            mas = self.match_master(typ)
        return typ, lay, mas

    @staticmethod
    def match_ph(phs, typ, idx):
        if idx is not None:
            for t, i, sp in phs:
                if i == idx:
                    return sp
        tt = {'ctrTitle': 'title'}.get(typ, typ)
        for t, i, sp in phs:
            if {'ctrTitle': 'title'}.get(t, t) == tt:
                return sp
        if typ in ('obj', 'body', 'subTitle'):
            for t, i, sp in phs:
                if t in ('body', 'obj', 'subTitle'):
                    return sp
        return None

    def match_master(self, typ):
        want = 'title' if typ in ('title', 'ctrTitle') else typ if typ in ('dt', 'ftr', 'sldNum', 'hdr') else 'body'
        for t, i, sp in self.ctx.master_ph:
            if t == want:
                return sp
        return None

    @staticmethod
    def style_cat(typ):
        if typ is None:
            return None
        if typ in ('title', 'ctrTitle'):
            return 'title'
        if typ in ('dt', 'ftr', 'sldNum', 'hdr'):
            return 'other'
        return 'body'

    # --- geometry ------------------------------------------------------------
    def xfrm_of(self, els):
        for e in els:
            if e is None:
                continue
            x = e.find('./p:spPr/a:xfrm', NS)
            if x is None:
                x = e.find('./p:grpSpPr/a:xfrm', NS)
            if x is not None and x.find('a:off', NS) is not None:
                return x
        return None

    def build_tree(self, tree, mapper, level, out):
        for ch in iter_tree(tree):
            t = ln(ch)
            try:
                if t in ('sp', 'cxnSp'):
                    e = self.build_sp(ch, mapper, level)
                elif t == 'pic':
                    e = self.build_pic(ch, mapper, level)
                elif t == 'grpSp':
                    e = self.build_grp(ch, mapper, level)
                elif t == 'graphicFrame':
                    e = None
                    warn('slide %d: skipped graphicFrame (table/chart/diagram)' % (self.si + 1))
                else:
                    e = None
            except Exception as ex:
                import traceback
                traceback.print_exc()
                warn('slide %d: failed shape: %s' % (self.si + 1, ex))
                e = None
            if e and level != 'slide' and mapper.__name__ == 'm' and self.off_canvas(e['box']):
                e = None
            if e:
                out.append(e)
        return out

    def off_canvas(self, b):
        cx, cy = b['x'] + b['w'] / 2, b['y'] + b['h'] / 2
        a = math.radians(b.get('rot') or 0)
        hw = abs(b['w'] / 2 * math.cos(a)) + abs(b['h'] / 2 * math.sin(a))
        hh = abs(b['w'] / 2 * math.sin(a)) + abs(b['h'] / 2 * math.cos(a))
        return cx + hw <= 0 or cy + hh <= 0 or cx - hw >= self.deck.W or cy - hh >= self.deck.H

    def nv(self, sp):
        return sp.find('./*/p:cNvPr', NS)

    def place(self, xfrm, mapper):
        off = xfrm.find('a:off', NS)
        ext = xfrm.find('a:ext', NS)
        x, y = int(off.get('x', 0)), int(off.get('y', 0))
        w, h = int(ext.get('cx', 0)), int(ext.get('cy', 0))
        rot = int(xfrm.get('rot', 0)) / 60000.0
        fh, fv = xfrm.get('flipH') in ('1', 'true'), xfrm.get('flipV') in ('1', 'true')
        return mapper(x, y, w, h, rot, fh, fv)

    def base_mapper(self):
        k = self.k

        def m(x, y, w, h, rot, fh, fv):
            return dict(x=x * k, y=y * k, w=w * k, h=h * k, rot=rot, fh=fh, fv=fv)
        return m

    # --- group -----------------------------------------------------------------
    def build_grp(self, g, mapper, level):
        nv = self.nv(g)
        if nv is not None and nv.get('hidden') in ('1', 'true'):
            return None
        xf = g.find('p:grpSpPr/a:xfrm', NS)
        if xf is None:
            box = dict(x=0, y=0, w=self.deck.W, h=self.deck.H, rot=0, fh=False, fv=False)
            ch_off, ch_ext, ext = (0, 0), (self.deck.cx, self.deck.cy), (self.deck.cx, self.deck.cy)
        else:
            box = self.place(xf, mapper)
            co, ce = xf.find('a:chOff', NS), xf.find('a:chExt', NS)
            ext_el = xf.find('a:ext', NS)
            ext = (int(ext_el.get('cx')), int(ext_el.get('cy')))
            ch_off = (int(co.get('x')), int(co.get('y'))) if co is not None else (0, 0)
            ch_ext = (int(ce.get('cx')), int(ce.get('cy'))) if ce is not None else ext
        sx = box['w'] / ch_ext[0] if ch_ext[0] else 0
        sy = box['h'] / ch_ext[1] if ch_ext[1] else 0
        gw, gh = box['w'], box['h']
        gfh, gfv = box['fh'], box['fv']

        def child_mapper(x, y, w, h, rot, fh, fv):
            cx = (x - ch_off[0]) * sx
            cy = (y - ch_off[1]) * sy
            cw, chh = w * sx, h * sy
            if gfh:
                cx = gw - cx - cw
                fh = not fh
                rot = -rot
            if gfv:
                cy = gh - cy - chh
                fv = not fv
                rot = -rot
            return dict(x=cx, y=cy, w=cw, h=chh, rot=rot, fh=fh, fv=fv)
        self.grp_fill_stack.append(g.find('p:grpSpPr', NS))
        kids = self.build_tree(g, child_mapper, level, [])
        self.grp_fill_stack.pop()
        if not kids:
            return None
        e = dict(kind='grp', box=dict(box, fh=False, fv=False), kids=kids)
        if level == 'slide' and nv is not None:
            e['id'] = nv.get('id')
        e['name'] = nv.get('name') if nv is not None else ''
        return e

    # --- fills / lines ---------------------------------------------------------
    def fill_spec(self, sppr_chain, style, w, h):
        """returns fill dict or None (no fill)."""
        for sppr in sppr_chain:
            if sppr is None:
                continue
            for ch in sppr:
                t = ln(ch)
                if t in ('noFill', 'solidFill', 'gradFill', 'blipFill', 'pattFill', 'grpFill'):
                    return self.fill_from(ch, None)
        if style is not None:
            fr = style.find('a:fillRef', NS)
            if fr is not None:
                idx = int(fr.get('idx', 0))
                ph = self.ctx.color_in(fr)
                if idx >= 1001:
                    lst = self.ctx.theme.bg_styles
                    idx -= 1000
                else:
                    lst = self.ctx.theme.fill_styles
                if 1 <= idx <= len(lst):
                    return self.fill_from(lst[idx - 1], ph)
        return None

    def fill_from(self, ch, ph):
        t = ln(ch)
        if t == 'noFill':
            return None
        if t == 'solidFill':
            c = self.ctx.color_in(ch, ph)
            return dict(type='solid', color=c) if c is not None else None
        if t == 'gradFill':
            stops = []
            for gs in ch.findall('a:gsLst/a:gs', NS):
                c = self.ctx.color_in(gs, ph)
                if c is not None:
                    stops.append((int(gs.get('pos', 0)) / 100000.0, c))
            stops.sort(key=lambda s: s[0])
            if not stops:
                return None
            lin = ch.find('a:lin', NS)
            path = ch.find('a:path', NS)
            g = dict(type='grad', stops=stops)
            if path is not None:
                ftr = path.find('a:fillToRect', NS)
                l = int(ftr.get('l', 0)) / 100000 if ftr is not None else 0.5
                t_ = int(ftr.get('t', 0)) / 100000 if ftr is not None else 0.5
                r = int(ftr.get('r', 0)) / 100000 if ftr is not None else 0.5
                b = int(ftr.get('b', 0)) / 100000 if ftr is not None else 0.5
                g.update(kind='radial', cx=(l + (1 - r)) / 2, cy=(t_ + (1 - b)) / 2, path=path.get('path'))
            else:
                g.update(kind='linear', ang=int(lin.get('ang', 0)) / 60000.0 if lin is not None else 90.0,
                         scaled=lin is not None and lin.get('scaled') in ('1', 'true'))
            return g
        if t == 'blipFill':
            return dict(type='blip', el=ch)
        if t == 'pattFill':
            c = self.ctx.color_in(ch.find('a:fgClr', NS), ph) or self.ctx.color_in(ch.find('a:bgClr', NS), ph)
            return dict(type='solid', color=c) if c is not None else None
        if t == 'grpFill':
            for gp in reversed(self.grp_fill_stack):
                if gp is None:
                    continue
                for c in gp:
                    if ln(c) in ('noFill', 'solidFill', 'gradFill', 'blipFill', 'pattFill'):
                        return self.fill_from(c, ph)
            return None
        return None

    def line_spec(self, sppr_chain, style):
        lns = [s.find('a:ln', NS) for s in sppr_chain if s is not None]
        lns = [l for l in lns if l is not None]
        base = None
        ph = None
        if style is not None:
            lr = style.find('a:lnRef', NS)
            if lr is not None:
                idx = int(lr.get('idx', 0))
                ph = self.ctx.color_in(lr)
                if 1 <= idx <= len(self.ctx.theme.ln_styles):
                    base = self.ctx.theme.ln_styles[idx - 1]
        chain = lns + ([base] if base is not None else [])
        if not chain:
            return None
        # fill: first explicit
        fill = None
        found = False
        for l in chain:
            for ch in l:
                if ln(ch) in ('noFill', 'solidFill', 'gradFill', 'pattFill'):
                    fill = self.fill_from(ch, ph if l is base else None)
                    found = True
                    break
            if found:
                break
        if fill is None:
            return None
        w = None
        for l in chain:
            if l.get('w') is not None:
                w = int(l.get('w'))
                break
        if w is None:
            w = 9525
        spec = dict(fill=fill, w=max(0.5, w * self.k) if w > 0 else 0.75 * self.pt)
        for l in chain:
            d = l.find('a:prstDash', NS)
            if d is not None:
                spec['dash'] = d.get('val')
                break
            cd = l.find('a:custDash', NS)
            if cd is not None:
                spec['cdash'] = [(int(ds.get('d', 0)) / 100000.0, int(ds.get('sp', 0)) / 100000.0) for ds in cd.findall('a:ds', NS)]
                break
        for l in chain:
            if l.get('cap'):
                spec['cap'] = l.get('cap')
                break
        for l in chain:
            for j in ('round', 'bevel', 'miter'):
                if l.find('a:' + j, NS) is not None:
                    spec['join'] = j
                    break
            if 'join' in spec:
                break
        for end in ('headEnd', 'tailEnd'):
            for l in chain:
                e = l.find('a:' + end, NS)
                if e is not None:
                    if e.get('type', 'none') != 'none':
                        spec[end] = (e.get('type'), e.get('w', 'med'), e.get('len', 'med'))
                    break
        return spec

    def effect_spec(self, sppr_chain, style):
        for s in sppr_chain:
            if s is None:
                continue
            el = s.find('a:effectLst', NS)
            if el is not None:
                return self.shadow_from(el, None)
        if style is not None:
            er = style.find('a:effectRef', NS)
            if er is not None:
                idx = int(er.get('idx', 0))
                if 1 <= idx <= len(self.ctx.theme.effect_styles):
                    es = self.ctx.theme.effect_styles[idx - 1].find('a:effectLst', NS)
                    return self.shadow_from(es, self.ctx.color_in(er))
        return None

    def shadow_from(self, el, ph):
        if el is None:
            return None
        sh = el.find('a:outerShdw', NS)
        if sh is not None:
            c = self.ctx.color_in(sh, ph)
            if c is None or c.a < 0.01:
                return None
            dist = int(sh.get('dist', 0)) * self.k
            ang = math.radians(int(sh.get('dir', 0)) / 60000.0)
            blur = int(sh.get('blurRad', 0)) * self.k
            return 'drop-shadow(%spx %spx %spx %s)' % (f2(dist * math.cos(ang)), f2(dist * math.sin(ang)), f2(blur / 2), c.css())
        gl = el.find('a:glow', NS)
        if gl is not None:
            c = self.ctx.color_in(gl, ph)
            if c is not None and c.a > 0.01:
                return 'drop-shadow(0 0 %spx %s)' % (f2(int(gl.get('rad', 0)) * self.k / 2), c.css())
        return None

    # --- svg helpers --------------------------------------------------------------
    def svg_paint(self, fill, w, h, defs):
        if fill is None:
            return 'none', None
        if fill['type'] == 'solid':
            c = fill['color']
            return c.hex(), (c.a if c.a < 0.999 else None)
        if fill['type'] == 'grad':
            gid = 'G%d_%d' % (self.si + 1, self.next_def())
            stops = ''.join('<stop offset="%s" stop-color="%s"%s/>' % (f2(p), c.hex(), (' stop-opacity="%s"' % f2(c.a)) if c.a < 0.999 else '')
                            for p, c in fill['stops'])
            if fill['kind'] == 'linear':
                a = math.radians(fill['ang'])
                dx, dy = math.cos(a), math.sin(a)
                L = abs(w * dx) + abs(h * dy)
                cx, cy = w / 2, h / 2
                x1, y1, x2, y2 = cx - dx * L / 2, cy - dy * L / 2, cx + dx * L / 2, cy + dy * L / 2
                defs.append('<linearGradient id="%s" gradientUnits="userSpaceOnUse" x1="%s" y1="%s" x2="%s" y2="%s">%s</linearGradient>'
                            % (gid, f2(x1), f2(y1), f2(x2), f2(y2), stops))
            else:
                cx, cy = fill['cx'] * w, fill['cy'] * h
                r = max(math.hypot(cx, cy), math.hypot(w - cx, cy), math.hypot(cx, h - cy), math.hypot(w - cx, h - cy))
                defs.append('<radialGradient id="%s" gradientUnits="userSpaceOnUse" cx="%s" cy="%s" r="%s">%s</radialGradient>'
                            % (gid, f2(cx), f2(cy), f2(r), stops))
            return 'url(#%s)' % gid, None
        return 'none', None

    def next_def(self):
        self.defs_id += 1
        return self.defs_id

    def css_paint(self, fill):
        if fill is None:
            return 'transparent'
        if fill['type'] == 'solid':
            return fill['color'].css()
        if fill['type'] == 'grad':
            stops = ', '.join('%s %s%%' % (c.css(), f2(p * 100)) for p, c in fill['stops'])
            if fill['kind'] == 'linear':
                return 'linear-gradient(%sdeg, %s)' % (f2(fill['ang'] + 90), stops)
            return 'radial-gradient(circle farthest-corner at %s%% %s%%, %s)' % (f2(fill['cx'] * 100), f2(fill['cy'] * 100), stops)
        return 'transparent'

    def marker(self, defs, spec, end, color):
        typ, wsz, lsz = spec[end]
        sw = spec['w']
        mw = ARROW_SIZE.get(wsz, 3.0)
        ml = ARROW_SIZE.get(lsz, 3.0)
        mid = 'M%d_%d' % (self.si + 1, self.next_def())
        # marker box in stroke-width units; tip at x=ml (end) pointing +x
        if typ in ('triangle', 'arrow', 'stealth'):
            if typ == 'triangle':
                shape = '<path d="M0 0L%s %sL0 %sZ" fill="%s"/>' % (f2(ml), f2(mw / 2), f2(mw), color)
            elif typ == 'stealth':
                shape = '<path d="M0 0L%s %sL0 %sL%s %sZ" fill="%s"/>' % (f2(ml), f2(mw / 2), f2(mw), f2(ml * 0.35), f2(mw / 2), color)
            else:
                shape = '<path d="M0.3 0.3L%s %sL0.3 %s" fill="none" stroke="%s" stroke-width="0.9" stroke-linecap="round" stroke-linejoin="round"/>' % (f2(ml - 0.3), f2(mw / 2), f2(mw - 0.3), color)
            refx = ml * (0.85 if typ != 'arrow' else 0.95)
        elif typ == 'diamond':
            shape = '<path d="M0 %sL%s 0L%s %sL%s %sZ" fill="%s"/>' % (f2(mw / 2), f2(ml / 2), f2(ml), f2(mw / 2), f2(ml / 2), f2(mw), color)
            refx = ml / 2
        else:  # oval
            shape = '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>' % (f2(ml / 2), f2(mw / 2), f2(ml / 2), f2(mw / 2), color)
            refx = ml / 2
        orient = 'auto' if end == 'tailEnd' else 'auto-start-reverse'
        defs.append('<marker id="%s" markerUnits="strokeWidth" markerWidth="%s" markerHeight="%s" refX="%s" refY="%s" orient="%s" overflow="visible">%s</marker>'
                    % (mid, f2(ml), f2(mw), f2(refx), f2(mw / 2), orient, shape))
        return mid

    def geometry_svg(self, paths, w, h, fill, line, flipH, flipV, shadow, extra_cls=''):
        """render geometry paths to an <svg> string"""
        if fill is None and line is None:
            return ''
        defs = []
        fpaint, fop = self.svg_paint(fill, w, h, defs) if fill and fill['type'] != 'blip' else ('none', None)
        sattrs = ''
        if line is not None:
            lp, lop = self.svg_paint(line['fill'], w, h, defs)
            sw = line['w']
            sattrs = ' stroke="%s" stroke-width="%s"' % (lp, f2(sw))
            if lop is not None:
                sattrs += ' stroke-opacity="%s"' % f2(lop)
            if line.get('dash') and line['dash'] in DASHES:
                pat = DASHES[line['dash']]
                if line.get('cap') == 'rnd' and line['dash'] in ('dot', 'sysDot'):
                    pat = [0.01, pat[1] + 1]
                sattrs += ' stroke-dasharray="%s"' % ' '.join(f2(v * sw) for v in pat)
            elif line.get('cdash'):
                sattrs += ' stroke-dasharray="%s"' % ' '.join('%s %s' % (f2(d * sw), f2(s * sw)) for d, s in line['cdash'])
            cap = {'rnd': 'round', 'sq': 'square', 'flat': 'butt'}.get(line.get('cap'), 'butt')
            sattrs += ' stroke-linecap="%s"' % cap
            sattrs += ' stroke-linejoin="%s"' % {'round': 'round', 'bevel': 'bevel', 'miter': 'miter'}.get(line.get('join'), 'round')
            col = line['fill']['color'].hex() if line['fill']['type'] == 'solid' else '#000'
            if line.get('headEnd'):
                sattrs += ' marker-start="url(#%s)"' % self.marker(defs, line, 'headEnd', col)
            if line.get('tailEnd'):
                sattrs += ' marker-end="url(#%s)"' % self.marker(defs, line, 'tailEnd', col)
        body = []
        for d, pf, ps in paths:
            a = ' d="%s"' % d
            a += ' fill="%s"' % (fpaint if pf else 'none')
            if pf and fop is not None:
                a += ' fill-opacity="%s"' % f2(fop)
            if ps and line is not None:
                a += sattrs
            elif line is not None and not ps:
                a += ' stroke="none"'
            body.append('<path%s/>' % a)
        tr = ''
        if flipH or flipV:
            tr = ' transform="translate(%s %s) scale(%d %d)"' % (f2(w if flipH else 0), f2(h if flipV else 0), -1 if flipH else 1, -1 if flipV else 1)
        style = ' style="filter:%s"' % shadow if shadow else ''
        return '<svg class="geo%s" width="%s" height="%s" aria-hidden="true"%s>%s<g%s>%s</g></svg>' % (
            extra_cls, f2(max(w, 1)), f2(max(h, 1)), style, ('<defs>%s</defs>' % ''.join(defs)) if defs else '', tr, ''.join(body))

    def shape_paths(self, sppr_chain, w, h, wemu, hemu):
        geom = None
        for s in sppr_chain:
            if s is None:
                continue
            g = s.find('a:prstGeom', NS)
            if g is None:
                g = s.find('a:custGeom', NS)
            if g is not None:
                geom = g
                break
        if geom is None:
            return preset_geometry('rect', w, h, {})
        if ln(geom) == 'prstGeom':
            av = {}
            for gd in geom.findall('a:avLst/a:gd', NS):
                m = re.match(r'val\s+(-?\d+)', gd.get('fmla', ''))
                if m:
                    av[gd.get('name')] = int(m.group(1))
            return preset_geometry(geom.get('prst'), w, h, av)
        return self.cust_paths(geom, w, h, wemu, hemu)

    def cust_paths(self, geom, w, h, wemu, hemu):
        gv, val = eval_guides(geom.findall('a:gdLst/a:gd', NS), geom.findall('a:avLst/a:gd', NS), wemu, hemu)
        out = []
        for path in geom.findall('a:pathLst/a:path', NS):
            pw, phh = int(path.get('w', 0) or 0), int(path.get('h', 0) or 0)
            sx = w / pw if pw else self.k
            sy = h / phh if phh else self.k
            pb = PB()

            def pt(el):
                return val(el.get('x')) * sx, val(el.get('y')) * sy
            for c in path:
                t = ln(c)
                pts = c.findall('a:pt', NS)
                if t == 'moveTo':
                    pb.M(*pt(pts[0]))
                elif t == 'lnTo':
                    pb.L(*pt(pts[0]))
                elif t == 'cubicBezTo':
                    (x1, y1), (x2, y2), (x3, y3) = [pt(p) for p in pts[:3]]
                    pb.C(x1, y1, x2, y2, x3, y3)
                elif t == 'quadBezTo':
                    (x1, y1), (x2, y2) = [pt(p) for p in pts[:2]]
                    pb.Qd(x1, y1, x2, y2)
                elif t == 'arcTo':
                    wr = val(c.get('wR')) * sx
                    hr = val(c.get('hR')) * sy
                    pb.arc(wr, hr, val(c.get('stAng')) / 60000.0, val(c.get('swAng')) / 60000.0)
                elif t == 'close':
                    pb.Z()
            fill_ok = path.get('fill', 'norm') != 'none'
            stroke_ok = path.get('stroke', '1') not in ('0', 'false')
            if pb.d:
                out.append((pb.s(), fill_ok, stroke_ok))
        tr = (0, 0, w, h)
        rect = geom.find('a:rect', NS)
        if rect is not None:
            try:
                tr = (val(rect.get('l')) * w / wemu if wemu else 0, val(rect.get('t')) * h / hemu if hemu else 0,
                      val(rect.get('r')) * w / wemu if wemu else w, val(rect.get('b')) * h / hemu if hemu else h)
            except Exception:
                tr = (0, 0, w, h)
        return out, tr

    # --- sp ---------------------------------------------------------------------
    def build_sp(self, sp, mapper, level):
        nv = self.nv(sp)
        if nv is not None and nv.get('hidden') in ('1', 'true'):
            return None
        typ, lay, mas = self.ph_chain(sp, level)
        is_ph = typ is not None
        if is_ph and level != 'slide':
            return None  # placeholders on layouts/masters are not rendered
        chain = [sp, lay, mas]
        xf = self.xfrm_of(chain)
        if xf is None:
            return None
        box = self.place(xf, mapper)
        w, h = box['w'], box['h']
        ext = xf.find('a:ext', NS)
        wemu, hemu = int(ext.get('cx', 0)), int(ext.get('cy', 0))
        sppr = [e.find('p:spPr', NS) if e is not None else None for e in chain]
        style = sp.find('p:style', NS)
        if style is None and lay is not None:
            style = lay.find('p:style', NS)
        fill = self.fill_spec(sppr, style, w, h)
        line = self.line_spec(sppr, style)
        shadow = self.effect_spec(sppr, style)
        paths, trect = self.shape_paths(sppr, w, h, wemu, hemu)
        e = dict(kind='sp', box=box, name=nv.get('name') if nv is not None else '')
        if level == 'slide' and nv is not None:
            e['id'] = nv.get('id')
        e['link'] = self.shape_link(nv)
        if fill is not None and fill['type'] == 'blip':
            # picture fill inside a geometry
            e['blipfill'] = self.blip_image(fill['el'], w, h)
            e['clip'] = paths[0][0] if paths else None
            fill_for_svg = None
        else:
            fill_for_svg = fill
        e['svg'] = self.geometry_svg(paths, w, h, fill_for_svg, line, box['fh'], box['fv'], shadow)
        txb = sp.find('p:txBody', NS)
        if txb is not None:
            text = self.build_text(txb, chain, typ, style, w, h, trect, box)
            if text:
                e['text'] = text
        if not e['svg'] and not e.get('text') and not e.get('blipfill'):
            return None
        return e

    def shape_link(self, nv):
        if nv is None:
            return None
        hl = nv.find('a:hlinkClick', NS)
        return self.link_target(hl)

    def link_target(self, hl):
        if hl is None:
            return None
        rid = hl.get(Q('r:id'))
        action = hl.get('action') or ''
        if 'hlinkshowjump' in action:
            jump = re.search(r'jump=(\w+)', action)
            return '#' + {'nextslide': 'next', 'previousslide': 'prev', 'firstslide': 'first', 'lastslide': 'last'}.get(jump.group(1).lower() if jump else '', 'next')
        if rid:
            rel = self.deck.pkg.rels(getattr(self, 'cur_part', self.ctx.part)).get(rid)
            if rel:
                if rel[2] == 'External':
                    return rel[1]
                if rel[0] == 'slide' and rel[1] in self.deck.slide_parts:
                    return '#/slide-%d' % (self.deck.slide_parts.index(rel[1]) + 1)
        return None

    # --- pictures --------------------------------------------------------------
    def blip_image(self, blipfill, w, h, part_owner=None):
        owner = part_owner or self.cur_part
        blip = blipfill.find('a:blip', NS)
        if blip is None:
            return None
        rels = self.deck.pkg.rels(owner)
        rid = blip.get(Q('r:embed')) or blip.get(Q('r:link'))
        target = rels.get(rid, (None, None, None))[1] if rid else None
        svg_target = None
        sb = blip.find('.//asvg:svgBlip', NS)
        if sb is not None:
            srid = sb.get(Q('r:embed'))
            if srid and srid in rels:
                svg_target = rels[srid][1]
        if target is None and svg_target is None:
            return None
        src = blipfill.find('a:srcRect', NS)
        crop = (0, 0, 0, 0)
        if src is not None:
            crop = tuple(int(src.get(s, 0)) / 100000.0 for s in ('l', 't', 'r', 'b'))
        eff = {}
        amf = blip.find('a:alphaModFix', NS)
        opacity = None
        if amf is not None:
            opacity = int(amf.get('amt', 100000)) / 100000.0
        duo = blip.find('a:duotone', NS)
        if duo is not None:
            cols = [self.ctx.color(c) for c in duo if ln(c) in COLOR_TAGS]
            if len(cols) == 2 and all(cols):
                eff['duotone'] = (cols[0].tup(), cols[1].tup())
        if blip.find('a:grayscl', NS) is not None:
            eff['gray'] = True
        lum = blip.find('a:lum', NS)
        if lum is not None and (lum.get('bright') or lum.get('contrast')):
            eff['bright'] = int(lum.get('bright', 0)) / 100000.0
            eff['contrast'] = int(lum.get('contrast', 0)) / 100000.0
        use_svg = svg_target if (svg_target and not eff) else None
        if target is None and use_svg is None:
            use_svg = svg_target
        tile = blipfill.find('a:tile', NS) is not None
        info = dict(crop=crop, opacity=opacity, tile=tile)
        if use_svg:
            info['key'] = self.deck.assets.image(target or svg_target, crop=None, disp=(w, h), prefer_svg=use_svg)
            info['css_crop'] = any(crop)
        else:
            if target.lower().endswith(('.emf', '.wmf')):
                info['key'] = self.deck.assets.image(target, crop=None, disp=(w, h))
                info['css_crop'] = any(crop)
            else:
                info['key'] = self.deck.assets.image(target, crop=crop if any(crop) else None, disp=(w, h),
                                                     effects=tuple(sorted(eff.items())) if eff else None)
                info['css_crop'] = False
        info['src_part'] = target
        return info

    def build_pic(self, pic, mapper, level):
        nv = self.nv(pic)
        if nv is not None and nv.get('hidden') in ('1', 'true'):
            return None
        typ, lay, mas = self.ph_chain(pic, level)
        if typ is not None and level != 'slide':
            return None
        chain = [pic, lay, mas]
        xf = self.xfrm_of(chain)
        if xf is None:
            return None
        box = self.place(xf, mapper)
        w, h = box['w'], box['h']
        ext = xf.find('a:ext', NS)
        wemu, hemu = int(ext.get('cx', 0)), int(ext.get('cy', 0))
        sppr = [e.find('p:spPr', NS) if e is not None else None for e in chain]
        style = pic.find('p:style', NS)
        bf = pic.find('p:blipFill', NS)
        img = self.blip_image(bf, w, h) if bf is not None else None
        line = self.line_spec(sppr, style)
        shadow = self.effect_spec(sppr, style)
        paths, _ = self.shape_paths(sppr, w, h, wemu, hemu)
        geom = None
        for s in sppr:
            if s is not None and s.find('a:prstGeom', NS) is not None:
                geom = s.find('a:prstGeom', NS)
                break
        e = dict(kind='pic', box=box, img=img, name=nv.get('name') if nv is not None else '')
        e['alt'] = (nv.get('descr') or '') if nv is not None else ''
        dec = nv.find('.//adec:decorative', NS) if nv is not None else None
        e['decorative'] = dec is not None and dec.get('val') in ('1', 'true')
        if level == 'slide' and nv is not None:
            e['id'] = nv.get('id')
        e['link'] = self.shape_link(nv)
        prst = geom.get('prst') if geom is not None else ('cust' if any(s is not None and s.find('a:custGeom', NS) is not None for s in sppr) else 'rect')
        if prst == 'roundRect':
            av = {}
            for gd in geom.findall('a:avLst/a:gd', NS):
                m = re.match(r'val\s+(-?\d+)', gd.get('fmla', ''))
                if m:
                    av[gd.get('name')] = int(m.group(1))
            e['radius'] = min(w, h) * min(50000, av.get('adj', 16667)) / 100000
        elif prst == 'ellipse':
            e['radius'] = 'ellipse'
        elif prst not in ('rect', None):
            e['clip'] = paths[0][0] if paths else None
        e['shadow'] = shadow
        e['border'] = self.geometry_svg(paths, w, h, None, line, box['fh'], box['fv'], None, ' border') if line else ''
        # media
        nvpr = pic.find('p:nvPicPr/p:nvPr', NS)
        vf = nvpr.find('a:videoFile', NS) if nvpr is not None else None
        media_part = None
        if nvpr is not None:
            pm = nvpr.find('.//p14:media', NS)
            rels = self.deck.pkg.rels(self.cur_part)
            if pm is not None and pm.get(Q('r:embed')) in rels:
                media_part = rels[pm.get(Q('r:embed'))][1]
            elif vf is not None and vf.get(Q('r:link')) in rels:
                r = rels[vf.get(Q('r:link'))]
                media_part = r[1] if r[2] != 'External' else None
        if vf is not None and media_part:
            e['video'] = self.deck.assets.media(media_part)
        elif img and img.get('src_part') and img['src_part'].lower().endswith('.gif') and self.deck.assets.has_transcoded(img['src_part']):
            e['video'] = self.deck.assets.media(img['src_part'])
            e['gifloop'] = True
        if e.get('video') and img and img.get('src_part') and any(img.get('crop') or ()):
            # poster without crop; the crop is applied to the <video> box with CSS
            e['vcrop'] = img['crop']
            img['key'] = self.deck.assets.image(img['src_part'], crop=None, disp=(w / max(0.05, 1 - img['crop'][0] - img['crop'][2]), h / max(0.05, 1 - img['crop'][1] - img['crop'][3])))
        if img is None and not e.get('video'):
            return None
        return e

    # --- text --------------------------------------------------------------------
    def build_text(self, txb, chain, typ, style, w, h, trect, box):
        paras = txb.findall('a:p', NS)
        if not any(p.find('a:r', NS) is not None or p.find('a:fld', NS) is not None for p in paras):
            # no runs at all: only keep if it has visible line breaks? skip
            if not any(p.find('a:br', NS) is not None for p in paras):
                return None
        sp, lay, mas = chain
        bodies = [e.find('p:txBody/a:bodyPr', NS) if e is not None else None for e in chain]
        bodies = [b for b in bodies if b is not None]

        def battr(name, default=None):
            for b in bodies:
                if b.get(name) is not None:
                    return b.get(name)
            return default
        lst = [e.find('p:txBody/a:lstStyle', NS) if e is not None else None for e in chain]
        cat = self.style_cat(typ)
        base = self.ctx.styles.get(cat) if cat else (self.ctx.default_style if self.ctx.default_style is not None else self.ctx.styles.get('other'))
        # fontRef as a synthetic defRPr
        fontref = None
        if style is not None:
            fr = style.find('a:fontRef', NS)
            if fr is not None:
                fontref = etree.Element(Q('a:defRPr'))
                idx = fr.get('idx')
                if idx in ('major', 'minor'):
                    lt = etree.SubElement(fontref, Q('a:latin'))
                    lt.set('typeface', '+mj-lt' if idx == 'major' else '+mn-lt')
                c = None
                for ch in fr:
                    if ln(ch) in COLOR_TAGS:
                        c = ch
                if c is not None:
                    sf = etree.Element(Q('a:solidFill'))
                    import copy as _copy
                    sf.append(_copy.deepcopy(c))
                    fontref.insert(0, sf)
        autofit = None
        for b in bodies:
            for t in ('normAutofit', 'spAutoFit', 'noAutofit'):
                a = b.find('a:' + t, NS)
                if a is not None:
                    autofit = a
                    break
            if autofit is not None:
                break
        fscale = 1.0
        lnred = 0.0
        if autofit is not None and ln(autofit) == 'normAutofit':
            fscale = int(autofit.get('fontScale', 100000)) / 100000.0
            lnred = int(autofit.get('lnSpcReduction', 0)) / 100000.0
        k = self.k
        ins = [int(battr(n, d)) * k for n, d in (('lIns', 91440), ('tIns', 45720), ('rIns', 91440), ('bIns', 45720))]
        anchor = battr('anchor', 't')
        wrap = battr('wrap', 'square') != 'none'
        vert = battr('vert', 'horz')
        tl, tt, tr_, tb = trect
        text = dict(left=tl, top=tt, width=max(0, tr_ - tl), height=max(0, tb - tt), pad=ins, anchor=anchor, wrap=wrap,
                    vert=vert if vert in ('vert', 'vert270', 'eaVert') else None, paras=[], fv=box['fv'],
                    fit=autofit is not None and ln(autofit) == 'normAutofit')
        brot = battr('rot')
        if brot:
            text['rot'] = int(brot) / 60000.0
        if battr('anchorCtr') in ('1', 'true'):
            text['anchorCtr'] = True
        numcol = int(battr('numCol', 1) or 1)
        if numcol > 1:
            text['cols'] = (numcol, int(battr('spcCol', 0)) * k)
        autonum = {}
        for pi, p in enumerate(paras):
            ppr = p.find('a:pPr', NS)
            lvl = int(ppr.get('lvl', 0)) if ppr is not None else 0
            n = lvl + 1
            lvl_chain = []
            for L in lst:
                if L is not None:
                    for tag in ('a:lvl%dpPr' % n, 'a:defPPr'):
                        x = L.find(tag, NS)
                        if x is not None:
                            lvl_chain.append(x)
            base_chain = []
            if base is not None:
                for tag in ('a:lvl%dpPr' % n, 'a:defPPr'):
                    x = base.find(tag, NS)
                    if x is not None:
                        base_chain.append(x)
            pchain = ([ppr] if ppr is not None else []) + lvl_chain + base_chain
            # run property chain (high -> low)
            rchain_tail = [x.find('a:defRPr', NS) for x in lvl_chain]
            rchain_tail = [x for x in rchain_tail if x is not None]
            if fontref is not None:
                rchain_tail.append(fontref)
            rchain_tail += [x.find('a:defRPr', NS) for x in base_chain if x.find('a:defRPr', NS) is not None]

            def pattr(name, default=None):
                for x in pchain:
                    if x.get(name) is not None:
                        return x.get(name)
                return default

            def pchild(tag):
                for x in pchain:
                    c = x.find('a:' + tag, NS)
                    if c is not None:
                        return c
                return None
            para = dict(pi=pi, algn=pattr('algn', 'l'), marL=int(pattr('marL', 0)) * k, indent=int(pattr('indent', 0)) * k,
                        runs=[], lvl=lvl)
            if ppr is not None and ppr.get('rtl') in ('1',):
                para['rtl'] = True
            # runs
            first_face = None
            first_size = None
            first_color = None
            for r in p:
                t = ln(r)
                if t not in ('r', 'fld', 'br'):
                    continue
                rpr = r.find('a:rPr', NS)
                rch = ([rpr] if rpr is not None else []) + rchain_tail
                if t == 'br':
                    rs = self.run_style(rch, fscale)
                    para['runs'].append(dict(br=True, size=rs['size']))
                    continue
                tnode = r.find('a:t', NS)
                txt = tnode.text if tnode is not None and tnode.text else ''
                rs = self.run_style(rch, fscale)
                run = dict(t=txt, st=rs)
                hl = rpr.find('a:hlinkClick', NS) if rpr is not None else None
                if hl is not None:
                    href = self.link_target(hl)
                    if href:
                        run['href'] = href
                        if not rs.get('explicit_color'):
                            hc = self.ctx.theme.colors.get(self.ctx.clrmap.get('hlink', 'hlink'))
                            if hc:
                                rs['color'] = hexrgb(hc).css()
                        rs['u'] = rs.get('u') or 'sng'
                para['runs'].append(run)
                if first_size is None and txt.strip():
                    first_face, first_size, first_color = rs['face'], rs['size'], rs['color']
            # end paragraph properties (size of empty lines)
            epr = p.find('a:endParaRPr', NS)
            es = self.run_style(([epr] if epr is not None else []) + rchain_tail, fscale)
            if first_size is None:
                first_size = es['size']
                first_face = es['face']
                first_color = es['color']
            para['empty_size'] = es['size']
            para['empty_face'] = es['face']
            # line spacing
            lf = line_factor(first_face)
            ls = pchild('lnSpc')
            lh = None
            if ls is not None:
                pc = ls.find('a:spcPct', NS)
                pp = ls.find('a:spcPts', NS)
                if pc is not None:
                    lh = ('f', max(0.1, int(pc.get('val')) / 100000.0 - lnred) * lf)
                elif pp is not None:
                    lh = ('px', int(pp.get('val')) / 100.0 * self.pt * (1 - lnred))
            if lh is None:
                lh = ('f', max(0.1, 1.0 - lnred) * lf)
            para['lh'] = lh

            def spacing(tag):
                s = pchild(tag)
                if s is None:
                    return 0.0
                pc = s.find('a:spcPct', NS)
                pp = s.find('a:spcPts', NS)
                if pp is not None:
                    return int(pp.get('val')) / 100.0 * self.pt
                if pc is not None:
                    return int(pc.get('val')) / 100000.0 * first_size * lf
                return 0.0
            para['sb'] = spacing('spcBef')
            para['sa'] = spacing('spcAft')
            # bullets
            has_text = any(r.get('t', '').strip() for r in para['runs'] if not r.get('br'))
            bu = None
            kind = self.first_of(pchain, ('buNone', 'buChar', 'buAutoNum', 'buBlip'))
            if kind in ('buChar', 'buAutoNum') and has_text:
                bfont_el = pchild('buFont')
                bface = bfont_el.get('typeface') if bfont_el is not None else None
                if bface and bface.startswith('+'):
                    bface = self.ctx.theme.fonts.get(bface, '')
                if kind == 'buChar':
                    ch = pchild('buChar').get('char', '\u2022')
                    char = map_symbol_char(ch, bface)
                    autonum.pop(lvl, None)
                else:
                    an = pchild('buAutoNum')
                    scheme = an.get('type', 'arabicPeriod')
                    start = int(an.get('startAt', 1))
                    prevn = autonum.get(lvl)
                    num = prevn[1] + 1 if prevn and prevn[0] == scheme else start
                    autonum[lvl] = (scheme, num)
                    char = format_autonum(scheme, num)
                    bface = None
                bcol = None
                if self.first_of(pchain, ('buClr', 'buClrTx')) == 'buClr':
                    c = self.ctx.color_in(pchild('buClr'))
                    bcol = c.css() if c else None
                bsize = first_size
                which = self.first_of(pchain, ('buSzPct', 'buSzPts', 'buSzTx'))
                if which == 'buSzPct':
                    bsize = first_size * int(pchild('buSzPct').get('val')) / 100000.0
                elif which == 'buSzPts':
                    bsize = int(pchild('buSzPts').get('val')) / 100.0 * self.pt
                bfc = None
                if bface and not bface.lower().startswith(('wingdings', 'symbol', 'webdings')):
                    bfc = font_class(bface)[0]
                bu = dict(char=char, color=bcol or first_color, size=bsize, fc=bfc)
            elif kind == 'buNone' or not has_text:
                autonum.pop(lvl, None)
            if bu:
                para['bu'] = bu
            text['paras'].append(para)
        # skip text blocks that only hold empty strings (but keep spacing paragraphs inside real text)
        if not any(r.get('t', '').strip() for pa in text['paras'] for r in pa['runs'] if not r.get('br')):
            return None
        return text

    @staticmethod
    def first_of(chain, tags):
        for x in chain:
            for c in x:
                if ln(c) in tags:
                    return ln(c)
        return None

    def run_style(self, rch, fscale=1.0):
        def attr(n, d=None):
            for x in rch:
                if x is not None and x.get(n) is not None:
                    return x.get(n)
            return d

        def child(tag):
            for x in rch:
                if x is None:
                    continue
                c = x.find('a:' + tag, NS)
                if c is not None:
                    return c, x
            return None, None
        sz = int(attr('sz', 1800)) / 100.0 * self.pt * fscale
        face = None
        for x in rch:
            lt = x.find('a:latin', NS) if x is not None else None
            if lt is not None and lt.get('typeface'):
                face = lt.get('typeface')
                break
        if face is None:
            face = '+mn-lt'
        if face.startswith('+'):
            face = self.ctx.theme.fonts.get(face, '') or self.ctx.theme.fonts.get('+mn-lt', 'Segoe UI')
        st = dict(size=sz, face=face)
        # colour: first fill element in chain (solid/grad/no)
        color = None
        explicit = False
        grad = None
        for x in rch:
            if x is None:
                continue
            found = None
            for c in x:
                if ln(c) in ('solidFill', 'gradFill', 'noFill'):
                    found = c
                    break
            if found is not None:
                if ln(found) == 'solidFill':
                    cc = self.ctx.color_in(found)
                    color = cc.css() if cc else None
                elif ln(found) == 'gradFill':
                    g = self.fill_from(found, None)
                    if g:
                        grad = self.css_paint(g)
                        color = g['stops'][0][1].css()
                else:
                    color = 'transparent'
                explicit = x is rch[0] if rch else False
                break
        if color is None:
            c = hexrgb(self.ctx.theme.colors.get(self.ctx.clrmap.get('tx1', 'dk1'), '000000'))
            color = c.css()
        st['color'] = color
        st['explicit_color'] = explicit
        if grad:
            st['grad'] = grad
        b = attr('b')
        st['b'] = b in ('1', 'true')
        st['i'] = attr('i') in ('1', 'true')
        u = attr('u')
        st['u'] = u if u and u != 'none' else None
        s = attr('strike')
        st['strike'] = s if s and s != 'noStrike' else None
        st['cap'] = attr('cap')
        spc = attr('spc')
        st['spc'] = int(spc) / 100.0 * self.pt if spc else 0
        bl = attr('baseline')
        st['baseline'] = int(bl) / 1000.0 if bl else 0
        hl, _ = child('highlight')
        if hl is not None:
            c = self.ctx.color_in(hl)
            st['hl'] = c.css() if c else None
        eff, _ = child('effectLst')
        if eff is not None:
            sh = eff.find('a:outerShdw', NS)
            if sh is not None:
                c = self.ctx.color_in(sh)
                if c is not None and c.a > 0.01:
                    dist = int(sh.get('dist', 0)) * self.k
                    ang = math.radians(int(sh.get('dir', 0)) / 60000.0)
                    st['shadow'] = '%spx %spx %spx %s' % (f2(dist * math.cos(ang)), f2(dist * math.sin(ang)), f2(int(sh.get('blurRad', 0)) * self.k / 2), c.css())
        lnel, _ = child('ln')
        if lnel is not None and lnel.find('a:solidFill', NS) is not None:
            c = self.ctx.color_in(lnel.find('a:solidFill', NS))
            if c is not None and c.a > 0.01:
                st['outline'] = (max(0.5, int(lnel.get('w', 9525)) * self.k), c.css())
        return st


def format_autonum(scheme, n):
    def roman(v):
        vals = [(1000, 'm'), (900, 'cm'), (500, 'd'), (400, 'cd'), (100, 'c'), (90, 'xc'), (50, 'l'), (40, 'xl'), (10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')]
        out = ''
        for a, s in vals:
            while v >= a:
                out += s
                v -= a
        return out
    if scheme.startswith('alphaLc'):
        core = chr(ord('a') + (n - 1) % 26)
    elif scheme.startswith('alphaUc'):
        core = chr(ord('A') + (n - 1) % 26)
    elif scheme.startswith('romanLc'):
        core = roman(n)
    elif scheme.startswith('romanUc'):
        core = roman(n).upper()
    else:
        core = str(n)
    if scheme.endswith('ParenBoth'):
        return '(%s)' % core
    if scheme.endswith('ParenR'):
        return core + ')'
    if scheme.endswith('Period'):
        return core + '.'
    if scheme.endswith('Minus'):
        return core + ' -'
    return core


# ----------------------------------------------------------------------------- animation
def cond_delay(ctn):
    d = 0
    sc = ctn.find('p:stCondLst', NS)
    if sc is not None:
        for c in sc.findall('p:cond', NS):
            v = c.get('delay')
            if v and v != 'indefinite' and c.get('evt') is None:
                try:
                    d = max(d, int(v))
                except ValueError:
                    pass
    return d


def dur_of(ctn):
    v = ctn.get('dur')
    if v is None or v == 'indefinite':
        return 0
    try:
        return int(v)
    except ValueError:
        return 0


def progress_fn(ctn):
    """returns f(p) with accel/decel/autoRev/repeat applied (p in 0..1 of total active time) and total multiplier"""
    acc = int(ctn.get('accel', 0)) / 100000.0
    dec = int(ctn.get('decel', 0)) / 100000.0
    rev = ctn.get('autoRev') in ('1', 'true')
    rc = ctn.get('repeatCount')
    reps = 1.0
    if rc and rc != 'indefinite':
        reps = max(1, int(rc)) / 1000.0
    s = acc + dec
    if s > 1:
        acc, dec = acc / s, dec / s
    vmax = 1.0 / (1 - acc / 2 - dec / 2) if (acc or dec) else 1.0

    def ease(t):
        if not (acc or dec):
            return t
        if t < acc:
            return vmax * t * t / (2 * acc)
        if t > 1 - dec:
            return 1 - vmax * (1 - t) ** 2 / (2 * dec)
        return vmax * (acc / 2 + (t - acc))

    def f(p):
        p = min(1.0, max(0.0, p)) * reps
        if p >= reps:
            q = 1.0 if (reps % 1 == 0) else reps % 1
        else:
            q = p % 1.0 if p < reps else 1.0
            if p > 0 and q == 0:
                q = 1.0
        if rev:
            q = q * 2 if q < 0.5 else (1 - q) * 2
        return ease(q)
    mult = reps * (2 if rev else 1)
    return f, mult


class AnimCompiler:
    def __init__(self, builder, geoms):
        self.b = builder
        self.geoms = geoms  # spid -> (cx, cy, w, h) in slide fractions

    def compile(self, slide_el):
        tm = slide_el.find('p:timing', NS)
        if tm is None:
            return [], [], {}
        root = tm.find('p:tnLst/p:par/p:cTn', NS)
        if root is None:
            return [], [], {}
        groups, inter, media = [], [], {}
        kids = root.find('p:childTnLst', NS)
        if kids is None:
            return [], [], {}
        for node in kids:
            t = ln(node)
            if t == 'seq':
                ctn = node.find('p:cTn', NS)
                nt = ctn.get('nodeType')
                if nt == 'mainSeq':
                    groups = self.groups_of(ctn)
                elif nt == 'interactiveSeq':
                    trig = ctn.find('p:stCondLst/p:cond/p:tgtEl/p:spTgt', NS)
                    inter.append(dict(trigger=trig.get('spid') if trig is not None else None, groups=self.groups_of(ctn)))
            elif t in ('video', 'audio'):
                cm = node.find('p:cMediaNode', NS)
                if cm is not None:
                    tg = cm.find('p:tgtEl/p:spTgt', NS)
                    ctn = cm.find('p:cTn', NS)
                    if tg is not None:
                        media[tg.get('spid')] = dict(loop=ctn is not None and ctn.get('repeatCount') == 'indefinite',
                                                     vol=int(cm.get('vol', 100000)) / 100000.0,
                                                     mute=cm.get('mute') in ('1', 'true'),
                                                     full=node.get('fullScrn') in ('1', 'true'))
        return groups, inter, media

    def groups_of(self, seq_ctn):
        out = []
        lst = seq_ctn.find('p:childTnLst', NS)
        if lst is None:
            return out
        for par in lst.findall('p:par', NS):
            g = par.find('p:cTn', NS)
            conds = g.findall('p:stCondLst/p:cond', NS)
            auto = any(c.get('evt') == 'onBegin' for c in conds) or (conds and all((c.get('delay') or '0') != 'indefinite' for c in conds) and not any(c.get('evt') for c in conds))
            fx = []
            sub = g.find('p:childTnLst', NS)
            if sub is not None:
                for sp in sub.findall('p:par', NS):
                    sctn = sp.find('p:cTn', NS)
                    sd = cond_delay(sctn)
                    eff_l = sctn.find('p:childTnLst', NS)
                    if eff_l is None:
                        continue
                    for ep in eff_l.findall('p:par', NS):
                        ectn = ep.find('p:cTn', NS)
                        e = self.effect(ectn, sd + cond_delay(ectn))
                        if e:
                            fx.append(e)
            if fx:
                out.append(dict(a=bool(auto), fx=fx))
        return out

    def behaviours(self, ctn, t0, out):
        lst = ctn.find('p:childTnLst', NS)
        if lst is None:
            return
        for b in lst:
            t = ln(b)
            if t == 'par':
                c = b.find('p:cTn', NS)
                self.behaviours(c, t0 + cond_delay(c), out)
                continue
            cb = b.find('p:cBhvr', NS)
            if cb is None:
                continue
            bc = cb.find('p:cTn', NS)
            d = dur_of(bc)
            start = t0 + cond_delay(bc)
            pf, mult = progress_fn(bc)
            tg = cb.find('p:tgtEl/p:spTgt', NS)
            tgt = None
            if tg is not None:
                tgt = dict(id=tg.get('spid'))
                pr = tg.find('p:txEl/p:pRg', NS)
                if pr is not None:
                    tgt['p'] = [int(pr.get('st')), int(pr.get('end'))]
            attrs = [a.text for a in cb.findall('p:attrNameLst/p:attrName', NS)]
            item = dict(kind=t, t=start, d=d * mult, pf=pf, attrs=attrs, tgt=tgt, fill=bc.get('fill'))
            if t == 'set':
                to = b.find('p:to', NS)
                v = to[0] if to is not None and len(to) else None
                item['to'] = v.get('val') if v is not None else None
            elif t == 'animEffect':
                item['tr'] = b.get('transition', 'in')
                item['filter'] = b.get('filter', 'fade')
            elif t == 'anim':
                tav = []
                for tv in b.findall('p:tavLst/p:tav', NS):
                    tm_ = tv.get('tm')
                    vv = tv.find('p:val', NS)
                    val = vv[0].get('val') if vv is not None and len(vv) else None
                    tav.append((int(tm_) / 100000.0 if tm_ and tm_ != 'indefinite' else None, val, tv.get('fmla')))
                if tav and tav[0][0] is None:
                    n = len(tav)
                    tav = [(i / max(1, n - 1), v, f) for i, (_, v, f) in enumerate(tav)]
                item['tav'] = tav
                item['frm'] = b.get('from')
                item['to'] = b.get('to')
                item['by'] = b.get('by')
                item['calc'] = b.get('calcmode', 'lin')
            elif t == 'animScale':
                def pair(tag):
                    e = b.find('p:' + tag, NS)
                    return (int(e.get('x')) / 100000.0, int(e.get('y')) / 100000.0) if e is not None else None
                item['by'], item['frm'], item['to'] = pair('by'), pair('from'), pair('to')
            elif t == 'animRot':
                item['by'] = int(b.get('by')) / 60000.0 if b.get('by') else None
                item['frm'] = int(b.get('from')) / 60000.0 if b.get('from') else None
                item['to'] = int(b.get('to')) / 60000.0 if b.get('to') else None
            elif t == 'animMotion':
                item['path'] = b.get('path', '')
            elif t == 'cmd':
                item['cmd'] = b.get('cmd', '')
                item['ctype'] = b.get('type')
            out.append(item)

    def effect(self, ectn, t0):
        cls = ectn.get('presetClass')
        beh = []
        self.behaviours(ectn, 0, beh)
        if not beh:
            return None
        tgt = next((b['tgt'] for b in beh if b['tgt']), None)
        if tgt is None:
            return None
        e = dict(tg=tgt, t=t0, c=cls or 'entr', tr=[], m=[])
        # media commands
        for b in beh:
            if b['kind'] == 'cmd':
                cmd = b['cmd']
                m = re.match(r'playFrom\(([\d.]+)\)', cmd)
                if m:
                    e['m'].append(dict(a='play', t=b['t'], f=float(m.group(1))))
                elif cmd in ('togglePause',):
                    e['m'].append(dict(a='toggle', t=b['t']))
                elif cmd in ('stop',):
                    e['m'].append(dict(a='stop', t=b['t']))
                elif cmd in ('pause',):
                    e['m'].append(dict(a='pause', t=b['t']))
                elif cmd in ('resume', 'play'):
                    e['m'].append(dict(a='play', t=b['t']))
        geo = self.geoms.get(tgt['id'], (0.5, 0.5, 0.1, 0.1))
        # visibility
        for b in beh:
            if b['kind'] == 'set' and 'style.visibility' in b['attrs']:
                vis = b['to'] == 'visible'
                e['tr'].append(dict(p='visibility', t=b['t'], d=max(1, b['d']), k=[[0, 'hidden' if vis else 'visible'], [1, 'visible' if vis else 'hidden']]))
        # opacity / filters
        for b in beh:
            if b['kind'] == 'animEffect':
                flt = (b['filter'] or 'fade').strip()
                inn = b['tr'] != 'out'
                d = max(1, b['d'])
                fname = flt.split('(')[0]
                arg = flt[flt.find('(') + 1:-1] if '(' in flt else ''
                clip = clip_frames(fname, arg)
                if clip:
                    kf = clip if inn else [[1 - o, v] for o, v in reversed(clip)]
                    e['tr'].append(dict(p='clipPath', t=b['t'], d=d, k=kf))
                else:
                    e['tr'].append(dict(p='opacity', t=b['t'], d=d, k=[[0, 0], [1, 1]] if inn else [[0, 1], [1, 0]]))
            elif b['kind'] == 'anim' and any(a in ('style.opacity',) for a in b['attrs']):
                kf = []
                for tm_, v, _ in b['tav']:
                    try:
                        kf.append([tm_, max(0, min(1, float(v)))])
                    except (TypeError, ValueError):
                        pass
                if len(kf) >= 2:
                    e['tr'].append(dict(p='opacity', t=b['t'], d=max(1, b['d']), k=kf))
            elif b['kind'] == 'set' and 'style.opacity' in b['attrs']:
                try:
                    v = float(b['to'])
                    e['tr'].append(dict(p='opacity', t=b['t'], d=max(1, b['d']), k=[[0, v], [1, v]]))
                except (TypeError, ValueError):
                    pass
        # transform (sampled)
        tb = [b for b in beh if (b['kind'] == 'anim' and any(a in ('ppt_x', 'ppt_y', 'ppt_w', 'ppt_h', 'style.rotation', 'r', 'ppt_r') for a in b['attrs']))
              or b['kind'] in ('animScale', 'animRot', 'animMotion')]
        if tb:
            T0 = min(b['t'] for b in tb)
            T1 = max(b['t'] + b['d'] for b in tb)
            if T1 <= T0:
                T1 = T0 + 1
            samples = sorted(set([T0, T1] + [T0 + (T1 - T0) * i / 24 for i in range(25)] + [b['t'] for b in tb] + [b['t'] + b['d'] for b in tb]))
            kf = []
            for ts in samples:
                v = self.transform_at(tb, ts, geo)
                kf.append([round((ts - T0) / (T1 - T0), 5), v])
            e['tr'].append(dict(p='transform', t=T0, d=T1 - T0, k=kf))
        e['tr'] = [dict(x, d=int(round(x['d'])), t=int(round(x['t']))) for x in e['tr']]
        for m in e['m']:
            m['t'] = int(round(m['t']))
        e['d'] = max([x['t'] + x['d'] for x in e['tr']] + [m['t'] for m in e['m']] + [0])
        return e

    def transform_at(self, tb, ts, geo):
        cx, cy, w, h = geo
        x, y, sw, sh, rot = cx, cy, 1.0, 1.0, 0.0
        sxm, sym = 1.0, 1.0
        for b in tb:
            if ts < b['t']:
                continue
            p = 1.0 if b['d'] <= 0 else min(1.0, (ts - b['t']) / b['d'])
            if ts > b['t'] + b['d'] and b.get('fill') == 'remove' and b['kind'] != 'anim':
                continue
            q = b['pf'](p)
            if b['kind'] == 'anim':
                attr = b['attrs'][0] if b['attrs'] else ''
                val = self.tav_value(b, q, geo, attr)
                if val is None:
                    continue
                if attr == 'ppt_x':
                    x = val
                elif attr == 'ppt_y':
                    y = val
                elif attr == 'ppt_w':
                    sw = val / w if w else 1
                elif attr == 'ppt_h':
                    sh = val / h if h else 1
                elif attr in ('style.rotation', 'r', 'ppt_r'):
                    rot = val
            elif b['kind'] == 'animScale':
                frm = b['frm'] or (1.0, 1.0)
                if b['to']:
                    to = b['to']
                elif b['by']:
                    to = (frm[0] * b['by'][0], frm[1] * b['by'][1])
                else:
                    to = frm
                sxm = frm[0] + (to[0] - frm[0]) * q
                sym = frm[1] + (to[1] - frm[1]) * q
            elif b['kind'] == 'animRot':
                if b['by'] is not None:
                    rot += b['by'] * q
                elif b['to'] is not None:
                    f0 = b['frm'] or 0
                    rot = f0 + (b['to'] - f0) * q
            elif b['kind'] == 'animMotion':
                dx, dy = motion_point(b['path'], q)
                x += dx
                y += dy
        dxp = (x - cx) * self.b.deck.W
        dyp = (y - cy) * self.b.deck.H
        return 'translate(%spx,%spx) rotate(%sdeg) scale(%s,%s)' % (f2(dxp), f2(dyp), f2(rot), f2r(sw * sxm), f2r(sh * sym))

    def tav_value(self, b, q, geo, attr):
        tav = b['tav']
        env = {'ppt_x': geo[0], 'ppt_y': geo[1], 'ppt_w': geo[2], 'ppt_h': geo[3]}
        if not tav:
            frm, to, by = b.get('frm'), b.get('to'), b.get('by')
            base = env.get(attr, 0)
            try:
                f0 = eval_anim(frm, env) if frm is not None else base
                if to is not None:
                    return f0 + (eval_anim(to, env) - f0) * q
                if by is not None:
                    return f0 + eval_anim(by, env) * q
            except Exception:
                return None
            return None
        vals = []
        for tm_, v, fm in tav:
            try:
                vals.append((tm_, eval_anim(v, env)))
            except Exception:
                return None
        if q <= vals[0][0]:
            return vals[0][1]
        for (t1, v1), (t2, v2) in zip(vals, vals[1:]):
            if t1 <= q <= t2:
                if b.get('calc') == 'discrete' or t2 == t1:
                    return v1
                return v1 + (v2 - v1) * (q - t1) / (t2 - t1)
        return vals[-1][1]


def f2r(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return s if s not in ('-0', '') else '0'


def eval_anim(expr, env):
    if expr is None:
        raise ValueError
    s = str(expr).strip()
    s = s.replace('#ppt_x', 'ppt_x').replace('#ppt_y', 'ppt_y').replace('#ppt_w', 'ppt_w').replace('#ppt_h', 'ppt_h')
    s = s.replace('^', '**')
    if not re.fullmatch(r"[\w\s\.\+\-\*/\(\),]*", s):
        raise ValueError(s)
    names = dict(env)
    names.update(sin=math.sin, cos=math.cos, tan=math.tan, asin=math.asin, acos=math.acos, atan=math.atan,
                 sqrt=math.sqrt, abs=abs, min=min, max=max, ln=math.log, exp=math.exp, pi=math.pi, e=math.e, rand=lambda x=1: 0.5 * x)
    return float(eval(s, {'__builtins__': {}}, names))


def motion_point(path, q):
    """approximate point along a PowerPoint motion path (relative slide units) at fraction q"""
    toks = re.findall(r'[MLCZEmlcze]|-?\d*\.?\d+(?:[eE]-?\d+)?', path or '')
    pts = []
    cur = (0.0, 0.0)
    i = 0
    segs = []
    cmd = None
    while i < len(toks):
        tk = toks[i]
        if tk.isalpha():
            cmd = tk.upper()
            i += 1
            if cmd in ('Z', 'E'):
                continue
            continue
        if cmd == 'M':
            cur = (float(toks[i]), float(toks[i + 1]))
            i += 2
        elif cmd == 'L':
            nxt = (float(toks[i]), float(toks[i + 1]))
            segs.append(('L', cur, nxt))
            cur = nxt
            i += 2
        elif cmd == 'C':
            c1 = (float(toks[i]), float(toks[i + 1]))
            c2 = (float(toks[i + 2]), float(toks[i + 3]))
            nxt = (float(toks[i + 4]), float(toks[i + 5]))
            segs.append(('C', cur, c1, c2, nxt))
            cur = nxt
            i += 6
        else:
            i += 1
    if not segs:
        return (0.0, 0.0)
    # sample uniformly per segment
    poly = []
    for s in segs:
        if s[0] == 'L':
            poly += [s[1], s[2]]
        else:
            p0, c1, c2, p3 = s[1:]
            for j in range(13):
                t = j / 12
                mt = 1 - t
                poly.append((mt ** 3 * p0[0] + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t ** 3 * p3[0],
                             mt ** 3 * p0[1] + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t ** 3 * p3[1]))
    lens = [0.0]
    for a, b in zip(poly, poly[1:]):
        lens.append(lens[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = lens[-1] or 1.0
    target = q * total
    for j in range(1, len(poly)):
        if lens[j] >= target:
            seg = lens[j] - lens[j - 1] or 1.0
            f = (target - lens[j - 1]) / seg
            return (poly[j - 1][0] + (poly[j][0] - poly[j - 1][0]) * f, poly[j - 1][1] + (poly[j][1] - poly[j - 1][1]) * f)
    return poly[-1]


def clip_frames(name, arg):
    if name == 'wipe':
        start = {'down': 'inset(0% 0% 100% 0%)', 'up': 'inset(100% 0% 0% 0%)', 'right': 'inset(0% 100% 0% 0%)', 'left': 'inset(0% 0% 0% 100%)'}.get(arg, 'inset(0% 0% 100% 0%)')
        return [[0, start], [1, 'inset(0% 0% 0% 0%)']]
    if name == 'barn':
        if 'Vertical' in arg:
            a = 'inset(0% 50% 0% 50%)'
        else:
            a = 'inset(50% 0% 50% 0%)'
        if arg.startswith('in'):
            a = 'inset(0% 0% 0% 0%)' if False else a
        return [[0, a], [1, 'inset(0% 0% 0% 0%)']]
    if name == 'box':
        return [[0, 'inset(50% 50% 50% 50%)'], [1, 'inset(0% 0% 0% 0%)']]
    if name == 'circle':
        return [[0, 'circle(0% at 50% 50%)'], [1, 'circle(71% at 50% 50%)']]
    if name == 'diamond':
        return [[0, 'polygon(50% 50%, 50% 50%, 50% 50%, 50% 50%)'], [1, 'polygon(50% -50%, 150% 50%, 50% 150%, -50% 50%)']]
    if name == 'plus':
        return [[0, 'polygon(50% 50%,50% 50%,50% 50%,50% 50%,50% 50%,50% 50%,50% 50%,50% 50%,50% 50%,50% 50%,50% 50%,50% 50%)'],
                [1, 'polygon(0% -100%,100% -100%,100% 0%,200% 0%,200% 100%,100% 100%,100% 200%,0% 200%,0% 100%,-100% 100%,-100% 0%,0% 0%)']]
    if name == 'slide':
        return None
    return None


# ----------------------------------------------------------------------------- HTML rendering
class Renderer:
    def __init__(self, deck):
        self.deck = deck

    def el_html(self, e, slide_no):
        b = e['box']
        st = 'left:%spx;top:%spx;width:%spx;height:%spx' % (f2(b['x']), f2(b['y']), f2(b['w']), f2(b['h']))
        if b.get('rot'):
            st += ';rotate:%sdeg' % f2(b['rot'])
        attrs = ''
        if e.get('id'):
            attrs += ' data-id="%s"' % e['id']
        cls = 'el'
        inner = ''
        if e['kind'] == 'grp':
            cls += ' grp'
            inner = ''.join(self.el_html(k, slide_no) for k in e['kids'])
        elif e['kind'] == 'sp':
            if e.get('blipfill'):
                inner += self.img_html(e['blipfill'], b['w'], b['h'], clip=e.get('clip'))
            inner += e.get('svg', '')
            if e.get('text'):
                inner += self.text_html(e['text'], b)
        elif e['kind'] == 'pic':
            cls += ' pic'
            inner = self.pic_html(e)
        html_ = '<div class="%s"%s style="%s">%s</div>' % (cls, attrs, st, inner)
        if e.get('link') and e['kind'] != 'grp':
            href = e['link']
            ext = href.startswith('http')
            html_ = '<div class="%s lnk"%s style="%s"><a class="shape-link" href="%s"%s>%s</a></div>' % (
                cls, attrs, st, esc(href), ' target="_blank" rel="noopener"' if ext else '', inner)
        return html_

    def img_html(self, info, w, h, clip=None, radius=None, alt='', decorative=True, shadow=None):
        if not info or not info.get('key'):
            return ''
        url = self.deck.assets.url(info['key'])
        if not url:
            return ''
        wrap = 'position:absolute;inset:0;overflow:hidden'
        if radius == 'ellipse':
            wrap += ';border-radius:50%'
        elif radius:
            wrap += ';border-radius:%spx' % f2(radius)
        if clip:
            wrap += ";clip-path:path('%s')" % clip
        if shadow:
            wrap_outer = 'position:absolute;inset:0;filter:%s' % shadow
        else:
            wrap_outer = None
        ist = ''
        if info.get('css_crop'):
            l, t, r, bb = info['crop']
            fw = w / max(0.0001, (1 - l - r))
            fh = h / max(0.0001, (1 - t - bb))
            ist = 'position:absolute;left:%spx;top:%spx;width:%spx;height:%spx;max-width:none' % (f2(-l * fw), f2(-t * fh), f2(fw), f2(fh))
        else:
            ist = 'position:absolute;inset:0;width:100%;height:100%'
        if info.get('opacity') is not None and info['opacity'] < 0.999:
            ist += ';opacity:%s' % f2(info['opacity'])
        if info.get('tile'):
            img = '<div style="position:absolute;inset:0;background:url(%s)"></div>' % url
        else:
            img = '<img data-src="%s" alt="%s" style="%s" draggable="false"%s>' % (esc(url), esc(alt or ''), ist, ' aria-hidden="true"' if decorative or not alt else '')
        out = '<div class="clip" style="%s">%s</div>' % (wrap, img)
        if wrap_outer:
            out = '<div style="%s">%s</div>' % (wrap_outer, out)
        return out

    def pic_html(self, e):
        b = e['box']
        w, h = b['w'], b['h']
        if e.get('video'):
            poster = self.deck.assets.url(e['img']['key']) if e.get('img') else ''
            wrap = 'position:absolute;inset:0;overflow:hidden'
            if e.get('radius') == 'ellipse':
                wrap += ';border-radius:50%'
            elif e.get('radius'):
                wrap += ';border-radius:%spx' % f2(e['radius'])
            vst = ''
            if e.get('vcrop'):
                l, t, r, bb = e['vcrop']
                fw = w / max(0.0001, (1 - l - r))
                fh = h / max(0.0001, (1 - t - bb))
                vst = ' style="left:%spx;top:%spx;width:%spx;height:%spx"' % (f2(-l * fw), f2(-t * fh), f2(fw), f2(fh))
            if e.get('gifloop'):
                v = ('<video class="gifv" data-src="%s" data-poster="%s" muted loop playsinline preload="none" aria-hidden="true"%s></video>'
                     % (esc(e['video']), esc(poster), vst))
            else:
                v = ('<video class="vid" data-src="%s" data-poster="%s" playsinline preload="none"%s%s></video>'
                     '<button class="vplay" type="button" aria-label="Play video"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z"/></svg></button><div class="vbar"><i></i></div>'
                     % (esc(e['video']), esc(poster), (' aria-label="%s"' % esc(e['alt'])) if e.get('alt') else '', vst))
            return '<div class="clip media" style="%s">%s</div>%s' % (wrap, v, e.get('border', ''))
        flip = ''
        if b.get('fh') or b.get('fv'):
            flip = 'transform:scale(%d,%d);' % (-1 if b.get('fh') else 1, -1 if b.get('fv') else 1)
        img = self.img_html(e['img'], w, h, clip=e.get('clip'), radius=e.get('radius'), alt=e.get('alt'), decorative=e.get('decorative'), shadow=e.get('shadow'))
        if flip:
            img = '<div style="position:absolute;inset:0;%s">%s</div>' % (flip, img)
        return img + e.get('border', '')

    def text_html(self, t, box):
        pad = t['pad']
        st = 'left:%spx;top:%spx;width:%spx;height:%spx;padding:%spx %spx %spx %spx' % (
            f2(t['left']), f2(t['top']), f2(t['width']), f2(t['height']), f2(pad[1]), f2(pad[2]), f2(pad[3]), f2(pad[0]))
        st += ';justify-content:%s' % {'t': 'flex-start', 'ctr': 'center', 'b': 'flex-end', 'just': 'center', 'dist': 'center'}.get(t['anchor'], 'flex-start')
        cls = 'tx'
        if not t['wrap']:
            cls += ' nw'
        if t.get('fit'):
            cls += ' fit'
        self.fit_mode = bool(t.get('fit'))
        rot = t.get('rot', 0)
        if t.get('fv'):
            rot += 180
        if rot:
            st += ';rotate:%sdeg' % f2(rot)
        if t.get('vert') == 'vert':
            st += ';writing-mode:vertical-rl'
        elif t.get('vert') == 'vert270':
            st += ';writing-mode:vertical-rl;transform:rotate(180deg)'
        ist = ''
        if t.get('cols'):
            ist = ' style="display:block;column-count:%d;column-gap:%spx"' % (t['cols'][0], f2(t['cols'][1]))
        parts = []
        for pa in t['paras']:
            parts.append(self.para_html(pa, t))
        self.fit_mode = False
        return '<div class="%s" style="%s"><div class="txi"%s>%s</div></div>' % (cls, st, ist, ''.join(parts))

    def run_css(self, s):
        fc, weight = font_class(s['face'])
        css = ['font-size:calc(%spx*var(--fs,1))' % f2(s['size'])] if getattr(self, 'fit_mode', False) else ['font-size:%spx' % f2(s['size'])]
        wgt = weight
        if s.get('b'):
            wgt = 700 if not weight or weight < 600 else max(700, weight)
        if wgt:
            css.append('font-weight:%d' % wgt)
        if s.get('i'):
            css.append('font-style:italic')
        if s.get('grad'):
            css.append('background:%s;-webkit-background-clip:text;background-clip:text;color:transparent' % s['grad'])
        else:
            css.append('color:%s' % s['color'])
        deco = []
        if s.get('u'):
            deco.append('underline')
        if s.get('strike'):
            deco.append('line-through')
        if deco:
            css.append('text-decoration:%s' % ' '.join(deco))
            if s.get('strike') == 'dblStrike':
                css.append('text-decoration-style:double')
            if s.get('u') in ('dbl',):
                css.append('text-decoration-style:double')
        if s.get('spc'):
            css.append('letter-spacing:%spx' % f2(s['spc']))
        if s.get('cap') == 'all':
            css.append('text-transform:uppercase')
        elif s.get('cap') == 'small':
            css.append('font-variant:small-caps')
        if s.get('baseline'):
            css.append('vertical-align:%s%%;font-size:%spx' % (f2(s['baseline']), f2(s['size'] * (0.66 if abs(s['baseline']) > 1 else 1))))
        if s.get('hl'):
            css.append('background-color:%s' % s['hl'])
        if s.get('shadow'):
            css.append('text-shadow:%s' % s['shadow'])
        if s.get('outline'):
            css.append('-webkit-text-stroke:%spx %s' % (f2(s['outline'][0]), s['outline'][1]))
        return fc, ';'.join(css)

    def para_html(self, pa, t):
        algn = {'l': 'left', 'ctr': 'center', 'r': 'right', 'just': 'justify', 'dist': 'justify', 'justLow': 'justify', 'thaiDist': 'justify'}.get(pa['algn'], 'left')
        css = ['text-align:%s' % algn]
        if pa['marL']:
            css.append('padding-left:%spx' % f2(pa['marL']))
        if pa['indent']:
            css.append('text-indent:%spx' % f2(pa['indent']))
        lh = pa['lh']
        css.append('line-height:%s' % (f2r(lh[1]) if lh[0] == 'f' else '%spx' % f2(lh[1])))
        if pa['sb'] and pa['pi'] > 0:
            css.append('margin-top:%spx' % f2(pa['sb']))
        if pa['sa']:
            css.append('margin-bottom:%spx' % f2(pa['sa']))
        if pa.get('rtl'):
            css.append('direction:rtl')
        if not t['wrap']:
            css.append('align-self:%s' % {'center': 'center', 'right': 'flex-end'}.get(algn, 'flex-start'))
        body = []
        if pa.get('bu'):
            bu = pa['bu']
            bst = 'font-size:%spx;color:%s;text-indent:0' % (f2(bu['size']), bu['color'])
            if pa['indent'] < 0:
                bst += ';width:%spx' % f2(-pa['indent'])
            else:
                bst += ';padding-right:0.4em'
            body.append('<span class="bu%s" style="%s" aria-hidden="true">%s</span>' % ((' ' + bu['fc']) if bu.get('fc') else '', bst, esc(bu['char'])))
        runs = pa['runs']
        has = False
        fit = getattr(self, 'fit_mode', False)

        def strut(sz):
            fs = ('calc(%spx*var(--fs,1))' % f2(sz)) if fit else ('%spx' % f2(sz))
            return '<span style="font-size:%s">&#8203;</span>' % fs
        last_br = False
        for r in runs:
            if r.get('br'):
                body.append(strut(r.get('size') or pa['empty_size']) + '<br>')
                last_br = True
                continue
            if r.get('t'):
                last_br = False
            txt = r['t']
            if txt == '':
                continue
            has = True
            fc, css_r = self.run_css(r['st'])
            span = '<span class="%s" style="%s">%s</span>' % (fc, css_r, esc(txt).replace('\v', '<br>'))
            if r.get('href'):
                ext = r['href'].startswith('http')
                span = '<a href="%s"%s>%s</a>' % (esc(r['href']), ' target="_blank" rel="noopener"' if ext else '', span)
            body.append(span)
        if not has or last_br:
            body.append(strut(pa['empty_size']))
        return '<p data-pi="%d" style="%s">%s</p>' % (pa['pi'], ';'.join(css), ''.join(body))


# ----------------------------------------------------------------------------- deck conversion
def slide_title(model_els):
    return ''


def collect_geoms(els, deck, ox=0.0, oy=0.0, out=None):
    out = {} if out is None else out
    for e in els:
        b = e['box']
        x, y = ox + b['x'], oy + b['y']
        if e.get('id'):
            out[e['id']] = ((x + b['w'] / 2) / deck.W, (y + b['h'] / 2) / deck.H, b['w'] / deck.W, b['h'] / deck.H)
        if e['kind'] == 'grp':
            collect_geoms(e['kids'], deck, x, y, out)
    return out


def text_of_shape(sp):
    return ' '.join(''.join(t.text or '' for t in p.iter(Q('a:t'))) for p in sp.iter(Q('a:p'))).strip()


def transition_of(slide_el):
    tr = None
    for ch in slide_el:
        if ln(ch) == 'AlternateContent':
            for c in resolve_alt(ch):
                if ln(c) == 'transition':
                    tr = c
        elif ln(ch) == 'transition':
            tr = ch
    if tr is None:
        return None
    dur = tr.get(Q('p14:dur'))
    spd = tr.get('spd', 'fast')
    d = int(dur) if dur is not None else {'fast': 500, 'med': 750, 'slow': 1000}.get(spd, 500)
    kind = None
    opt = {}
    for c in tr:
        if not isinstance(c.tag, str):
            continue
        kind = ln(c)
        if kind == 'fade' and c.get('thruBlk') in ('1', 'true'):
            opt['black'] = 1
        if c.get('dir'):
            opt['dir'] = c.get('dir')
        break
    if kind is None or d <= 0:
        return None
    if kind not in ('fade', 'push', 'wipe', 'cover', 'pull', 'zoom', 'cut', 'split', 'dissolve', 'randomBar', 'morph'):
        kind = 'fade'
    if kind in ('dissolve', 'randomBar', 'morph'):
        kind = 'fade'
    if kind == 'cut':
        return None
    out = dict(type=kind, d=d)
    out.update(opt)
    return out


def notes_html(deck, slide_part):
    np_ = deck.pkg.rel_of_type(slide_part, 'notesSlide')
    if not np_:
        return ''
    root = deck.pkg.xml(np_)
    for sp in root.iter(Q('p:sp')):
        ph = sp.find('./p:nvSpPr/p:nvPr/p:ph', NS)
        if ph is not None and ph.get('type') == 'body':
            paras = []
            for p in sp.iter(Q('a:p')):
                txt = ''
                for r in p:
                    if ln(r) in ('r', 'fld'):
                        t = r.find('a:t', NS)
                        txt += t.text if t is not None and t.text else ''
                    elif ln(r) == 'br':
                        txt += '\n'
                if txt.strip():
                    ppr = p.find('a:pPr', NS)
                    lvl = int(ppr.get('lvl', 0)) if ppr is not None else 0
                    paras.append('<p class="nl%d">%s</p>' % (min(lvl, 3), esc(txt).replace('\n', '<br>')))
            return ''.join(paras)
    return ''


def background_of(builder, ctx):
    for src, part in ((ctx.el, ctx.part), (ctx.layout, ctx.layout_part), (ctx.master, ctx.master_part)):
        bg = src.find('p:cSld/p:bg', NS)
        if bg is None:
            continue
        bp = bg.find('p:bgPr', NS)
        if bp is not None:
            for ch in bp:
                t = ln(ch)
                if t == 'blipFill':
                    builder.cur_part = part
                    info = builder.blip_image(ch, builder.deck.W, builder.deck.H)
                    return dict(kind='img', info=info)
                if t in ('solidFill', 'gradFill', 'noFill', 'pattFill'):
                    f = builder.fill_from(ch, None)
                    return dict(kind='css', css=builder.css_paint(f) if f else '#ffffff')
        br = bg.find('p:bgRef', NS)
        if br is not None:
            idx = int(br.get('idx', 0))
            ph = ctx.color_in(br)
            lst = ctx.theme.bg_styles if idx >= 1001 else ctx.theme.fill_styles
            i = idx - 1000 if idx >= 1001 else idx
            if 1 <= i <= len(lst):
                f = builder.fill_from(lst[i - 1], ph)
                if f and f['type'] == 'blip':
                    builder.cur_part = ctx.master_part
                    return dict(kind='img', info=builder.blip_image(f['el'], builder.deck.W, builder.deck.H))
                return dict(kind='css', css=builder.css_paint(f) if f else '#ffffff')
            if ph is not None:
                return dict(kind='css', css=ph.css())
    return dict(kind='css', css='#ffffff')


def convert(deck, title, slug):
    slides = []
    shown = 0
    for si, part in enumerate(deck.slide_parts):
        sel = deck.pkg.xml(part)
        hidden = sel.get('show') in ('0', 'false')
        if hidden and not deck.include_hidden:
            continue
        ctx = SlideCtx(deck, part)
        b = Builder(deck, ctx, shown)
        b.grp_fill_stack = []
        els = []
        show_master = sel.get('showMasterSp') not in ('0', 'false')
        if show_master:
            if ctx.layout.get('showMasterSp') not in ('0', 'false'):
                b.cur_part = ctx.master_part
                b.build_tree(ctx.master.find('p:cSld/p:spTree', NS), b.base_mapper(), 'master', els)
            b.cur_part = ctx.layout_part
            b.build_tree(ctx.layout.find('p:cSld/p:spTree', NS), b.base_mapper(), 'layout', els)
        n_bg = len(els)
        b.cur_part = part
        b.build_tree(sel.find('p:cSld/p:spTree', NS), b.base_mapper(), 'slide', els)
        bg = background_of(b, ctx)
        # title
        title_txt = ''
        for sp in sel.iter(Q('p:sp')):
            ph = sp.find('./p:nvSpPr/p:nvPr/p:ph', NS)
            if ph is not None and ph.get('type') in ('title', 'ctrTitle'):
                title_txt = text_of_shape(sp)
                break
        if not title_txt:
            for sp in sel.iter(Q('p:sp')):
                tt = text_of_shape(sp)
                if tt:
                    title_txt = tt[:80]
                    break
        geoms = collect_geoms(els[n_bg:], deck)
        groups, inter, media = AnimCompiler(b, geoms).compile(sel)
        # initial visibility: first effect per target
        first = {}
        order = []
        for g in groups:
            for fx in g['fx']:
                key = json.dumps(fx['tg'], sort_keys=True)
                if key not in first:
                    first[key] = fx
                    order.append(key)
        init = [first[k]['tg'] for k in order if first[k]['c'] == 'entr' and any(t['p'] == 'visibility' for t in first[k]['tr'])]
        # drop interactive sequences that only toggle a video (the player handles clicks)
        inter = [s for s in inter if not all(all(not fx['tr'] and fx['m'] for fx in g['fx']) for g in s['groups'])]
        slides.append(dict(n=shown + 1, src=si + 1, title=title_txt, els=els, bg=bg, tr=transition_of(sel), g=groups,
                           inter=inter, media=media, init=init, notes=notes_html(deck, part), hidden=hidden))
        shown += 1
    return slides


def render_deck(deck, slides, title, slug, runtime_css, runtime_js, description='', home_href='../'):
    R = Renderer(deck)
    secs = []
    data = dict(w=deck.W, h=deck.H, title=title, slug=slug, slides=[])
    for s in slides:
        bg = s['bg']
        if bg['kind'] == 'img' and bg.get('info'):
            url = deck.assets.url(bg['info']['key'])
            bg_html = '<div class="bg"><img data-src="%s" alt="" aria-hidden="true" draggable="false"></div>' % esc(url)
        else:
            bg_html = '<div class="bg" style="background:%s"></div>' % (bg.get('css') or '#fff')
        body = ''.join(R.el_html(e, s['n']) for e in s['els'])
        secs.append('<section class="slide" id="slide-%d" data-n="%d" role="group" aria-roledescription="slide" aria-label="%s" aria-hidden="true">%s%s</section>'
                    % (s['n'], s['n'], esc('%d: %s' % (s['n'], s['title'] or 'Slide')), bg_html, body))
        data['slides'].append(dict(n=s['n'], title=s['title'], tr=s['tr'], g=s['g'], init=s['init'], media=s['media'],
                                   inter=s['inter'], notes=s['notes']))
    css = runtime_css.replace('/*FONTS*/', font_css())
    js_data = json.dumps(data, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
    thumb0 = 'assets/thumbs/cover.jpg'
    doc = TEMPLATE.format(title=esc(title), desc=esc(description or title), css=css, slides='\n'.join(secs), data=js_data,
                          js=runtime_js, W=deck.W, H=deck.H, thumb=thumb0, home=esc(home_href), count=len(slides))
    return doc


TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{thumb}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#000000">
<style>
{css}
</style>
</head>
<body>
<a class="skip" href="#deck">Skip to slides</a>
<main id="deck" class="deck" tabindex="-1" aria-label="{title}">
<div class="viewport"><div class="stage" style="width:{W}px;height:{H}px">
{slides}
</div></div>
</main>
<div class="hud" aria-label="Presentation controls">
  <a class="hbtn home" href="{home}" title="All decks" aria-label="All decks"><svg viewBox="0 0 24 24"><path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"/></svg></a>
  <button class="hbtn prev" type="button" title="Previous (Left arrow)" aria-label="Previous"><svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg></button>
  <span class="count" aria-live="polite"><b class="cur">1</b> / <span class="tot">{count}</span></span>
  <button class="hbtn next" type="button" title="Next (Right arrow / Space)" aria-label="Next"><svg viewBox="0 0 24 24"><path d="M9 5l7 7-7 7"/></svg></button>
  <span class="sep"></span>
  <button class="hbtn ov" type="button" title="All slides (O)" aria-label="All slides"><svg viewBox="0 0 24 24"><path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/></svg></button>
  <button class="hbtn nt" type="button" title="Speaker notes (N)" aria-label="Speaker notes"><svg viewBox="0 0 24 24"><path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5"/></svg></button>
  <button class="hbtn fs" type="button" title="Full screen (F)" aria-label="Full screen"><svg viewBox="0 0 24 24"><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/></svg></button>
  <button class="hbtn hp" type="button" title="Keyboard shortcuts (?)" aria-label="Keyboard shortcuts"><svg viewBox="0 0 24 24"><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17.5v.5"/></svg></button>
</div>
<div class="progress" aria-hidden="true"><i></i></div>
<aside class="notes" aria-label="Speaker notes" hidden><div class="notes-head"><b>Speaker notes</b><span class="nslide"></span><button type="button" class="nclose" aria-label="Close notes">&times;</button></div><div class="notes-body"></div></aside>
<div class="overview" role="dialog" aria-label="All slides" hidden><div class="ov-head"><b>{title}</b><button type="button" class="ovclose" aria-label="Close">&times;</button></div><div class="ov-grid"></div></div>
<div class="help" role="dialog" aria-label="Keyboard shortcuts" hidden><div class="help-card"><h2>Keyboard shortcuts</h2>
<dl><dt>&rarr; &darr; Space PgDn Enter, click</dt><dd>Next animation / slide</dd><dt>&larr; &uarr; PgUp Backspace</dt><dd>Previous</dd>
<dt>Home / End</dt><dd>First / last slide</dd><dt>number + Enter</dt><dd>Go to slide</dd><dt>O or G</dt><dd>All slides</dd><dt>N</dt><dd>Speaker notes</dd>
<dt>F</dt><dd>Full screen</dd><dt>B / W</dt><dd>Black / white screen</dd><dt>Esc</dt><dd>Close panel</dd></dl><button type="button" class="hclose">Close</button></div></div>
<div class="blank" hidden></div>
<script type="application/json" id="deck-data">{data}</script>
<script>
{js}
</script>
</body>
</html>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pptx')
    ap.add_argument('outdir')
    ap.add_argument('--title', required=True)
    ap.add_argument('--slug', required=True)
    ap.add_argument('--desc', default='')
    ap.add_argument('--media-dir')
    ap.add_argument('--include-hidden', action='store_true')
    ap.add_argument('--no-notes', action='store_true', help='leave speaker notes out of the page')
    ap.add_argument('--runtime', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runtime'))
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    deck = Deck(a.pptx, a.outdir, a.media_dir, a.include_hidden)
    print('converting', a.pptx, '->', a.outdir, '(%dx%d)' % (deck.W, deck.H))
    slides = convert(deck, a.title, a.slug)
    if a.no_notes:
        for s in slides:
            s['notes'] = ''
    total = deck.assets.finalize()
    print('  slides: %d, images: %d (%.1f MB)' % (len(slides), len(deck.assets.urls), total / 1e6))
    css = open(os.path.join(a.runtime, 'deck.css'), encoding='utf8').read()
    js = open(os.path.join(a.runtime, 'deck.js'), encoding='utf8').read()
    doc = render_deck(deck, slides, a.title, a.slug, css, js, a.desc)
    with open(os.path.join(a.outdir, 'index.html'), 'w', encoding='utf8') as fh:
        fh.write(doc)
    meta = dict(title=a.title, slug=a.slug, slides=[dict(n=s['n'], title=s['title'], src=s['src']) for s in slides])
    with open(os.path.join(a.outdir, 'deck.json'), 'w', encoding='utf8') as fh:
        json.dump(meta, fh, indent=1)
    print('  html: %.2f MB' % (len(doc.encode('utf8')) / 1e6))


if __name__ == '__main__':
    main()
