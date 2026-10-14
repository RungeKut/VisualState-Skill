# -*- coding: utf-8 -*-
"""Раскладка диаграммы состояний для vskit.design (format 11).

Единицы — 0,1 мм (как в .vsr). Соглашения Designer 9.1 (проверены по
снимкам):
  * position вершины — координаты в системе региона (начало региона —
    под заголовком родителя, на LABEL_H ниже его верхней грани);
  * подпись перехода (transitionProperties/position) — относительно рамки
    ИСТОЧНИКА, порядок атрибутов bottom,left,right,top; текст прижат к
    левому верхнему углу бокса;
  * routePoints: все точки, кроме последней, — относительно рамки
    источника, последняя — относительно рамки цели.

Правила раскладки региона:
  1. Размер состояния растёт от текста entry/exit/internal.
  2. Слои — по самому длинному пути, циклы разорваны DFS; «кольцо»
     (у всех состояний ровно по одной входящей и исходящей) — одной
     строкой. Начальная вершина стоит над своей целью, не в слое.
  3. Типы рёбер:
       down  — в соседний слой: вертикаль или Z через «дорожку» в
               промежутке между рядами, подпись над дорожкой;
       flat  — соседи в одной строке, слева направо: стрелка в зазоре,
               подпись над стрелкой; зазор шире подписи;
       top / bot — остальные рёбра внутри строки: дорожка над / под
               строкой;
       back  — вверх: общий правый канал на каждую цель («шина»),
               подпись над отводом от источника;
       skip  — вниз через слои: общий левый канал на цель.
  4. Подписи не накладываются на состояния: под каждую выделено место.
  5. Несколько рёбер на одной грани — разные порты.
Межрегиональные переходы — двухточечные (середину не выразить).
"""
import re

MARGIN = 53
PSEUDO = 53
LINE_H = 40
WRAP = 21
LABEL_W = 500
PORT_STEP = 80
LANE_PAD = 30
INTERIOR_X = 0
INTERIOR_Y = 42
GAP_MIN = 160
GAP_X_MIN = 200
CH_STEP = 70
INIT_UP = 70
BULGE = 45
SPLINE_PROPS = 809894017

_CALL = re.compile(r"^\s*([A-Za-z_]\w*)\s*\(")


def _text_of(t):
    s = t.trigger if t.trigger else "trigger"
    if t.special == "else":
        s += " [else]"
    elif t.guards:
        s += " [" + "] [".join(t.guards) + "]"
    if t.do:
        parts = []
        for x in t.do:
            x = x.rstrip(";").strip()
            parts.append(x if _CALL.match(x) else "[%s]" % x)
        s += " / " + " ".join(parts)
    return s


def _wrap(s, width=WRAP):
    if not s:
        return []
    words, lines, cur = s.split(" "), [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if len(cand) <= width:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _lh(t):
    return len(_wrap(_text_of(t))) * LINE_H + 20


def _body_lines(v, width):
    out = []
    if v.entry:
        out += _wrap("Entry / " + " ".join(
            x.rstrip(";") + ";" for x in v.entry), width)
    for t in v.trans:
        if t.kind == "internal":
            out += _wrap("Internal: " + _text_of(t), width)
    if v.exit:
        out += _wrap("Exit / " + " ".join(
            x.rstrip(";") + ";" for x in v.exit), width)
    return out


def _leaf_size(v, w0, h0, label_h):
    width = 36
    lines = _body_lines(v, width)
    if len(lines) > 6:
        width = 52
        lines = _body_lines(v, width)
    w = w0 if width == 36 else int(w0 * 1.45)
    h = label_h + 40 + len(lines) * LINE_H + 40
    return w, max(h0, h)


PH_W, PH_H = 700, 260


def _crossed_regions(mach, where):
    """Регионы, через границу поддерева которых идёт переход."""
    vsets = {}

    def gather(r):
        s = set()
        for v in r.vertices:
            s.add(id(v))
            for sub in v.regions:
                s |= gather(sub)
        vsets[id(r)] = s
        return s
    gather(mach.top)
    crossed = set()
    for path, v, r in mach._walk():
        for t in v.trans:
            if t.kind == "external" and t.target:
                tg, _tr = where[t.target]
                for rid, s in vsets.items():
                    if (id(v) in s) != (id(tg) in s):
                        crossed.add(rid)
    return crossed


def layout(mach):
    global _CROSSED
    where = {}
    for path, v, r in mach._walk():
        where[path] = (v, r)
    _CROSSED = _crossed_regions(mach, where)
    _region(mach.top, where)


_CROSSED = set()


class Edge:
    def __init__(self, i, j, t):
        self.i, self.j, self.t = i, j, t
        self.kind = None
        self.lh = _lh(t)


def _region(r, where):
    from .design import STATE_W, STATE_H, LABEL_H
    for v in r.vertices:
        for sub in v.regions:
            _region(sub, where)
        if v.kind == "state":
            if len(v.regions) >= 2:
                for sub in v.regions:
                    sub.off_page = id(sub) not in _CROSSED
            if v.regions:
                ew = [PH_W if getattr(s, "off_page", False) else s.w
                      for s in v.regions]
                eh = [PH_H if getattr(s, "off_page", False) else s.h
                      for s in v.regions]
                v.w = max(STATE_W, sum(ew) + MARGIN * (len(v.regions) + 1))
                v.h = LABEL_H + max(eh) + 2 * MARGIN
                for t in v.trans:
                    if t.kind == "external" and t.target:
                        tg, treg = where[t.target]
                        if any(tg in reg.vertices for reg in v.regions):
                            v.w = max(v.w, INTERIOR_X + tg.x + tg.w // 2
                                      + 14 + LABEL_W + MARGIN)
            else:
                v.w, v.h = _leaf_size(v, STATE_W, STATE_H, LABEL_H)
        else:
            v.w = v.h = PSEUDO
    if not r.vertices:
        r.w = r.h = 2 * MARGIN + PSEUDO
        return
    body = [v for v in r.vertices if v.kind != "initialState"]
    inits = [v for v in r.vertices if v.kind == "initialState"]
    idx = {id(v): k for k, v in enumerate(body)}
    edges = []
    for k, v in enumerate(body):
        for t in v.trans:
            if t.kind != "external" or t.target is None:
                continue
            tg, _r = where[t.target]
            if id(tg) in idx:
                edges.append(Edge(k, idx[id(tg)], t))
    layer = _layers(body, [(e.i, e.j, e.t) for e in edges])
    _classify(body, edges, layer)
    _place(r, body, inits, edges, layer, where, idx)
    for v in r.vertices:
        for t in v.trans:
            if t.kind != "external" or t.target is None:
                continue
            tg, treg = where[t.target]
            if treg is not r and not hasattr(t, "_route"):
                t._route, t._label = _route_cross(v, tg, t)


def _classify(body, edges, layer):
    pair_flat = set()
    for e in edges:
        v, tg = body[e.i], body[e.j]
        lv, lt = layer[id(v)], layer[id(tg)]
        if e.i == e.j:
            e.kind = "self"
        elif getattr(e.t, "_ring_wrap", False):
            e.kind = "bot"
        elif lt == lv:
            d = tg._ord - v._ord
            key = frozenset((e.i, e.j))
            if abs(d) == 1 and key not in pair_flat:
                pair_flat.add(key)
                e.kind = "flat"
            else:
                e.kind = "top" if d > 0 else "bot"
        elif lt == lv + 1:
            e.kind = "down"
        elif lt > lv + 1:
            e.kind = "skip"
        else:
            e.kind = "back"


def _ports(count, size, step=PORT_STEP):
    if count <= 1:
        return [0] * count
    span = min(step * (count - 1), max(size - 120, size // 2))
    s = span / (count - 1)
    return [int(-span / 2 + k * s) for k in range(count)]


def _lane_h(lst):
    return sum(e.lh + LANE_PAD for e in lst) + (2 * LANE_PAD if lst else 0)


def _place(r, body, inits, edges, layer, where, idx):
    rows = {}
    for v in body:
        rows.setdefault(layer[id(v)], []).append(v)
    for l in rows:
        rows[l].sort(key=lambda v: v._ord)
    order = sorted(rows)
    by_kind = {}
    for e in edges:
        by_kind.setdefault(e.kind, []).append(e)

    right_stub, left_stub = {}, {}
    for e in by_kind.get("back", []) + by_kind.get("self", []):
        right_stub.setdefault(e.i, []).append(e)
    for e in by_kind.get("skip", []):
        left_stub.setdefault(e.i, []).append(e)
    for k, lst in list(right_stub.items()) + list(left_stub.items()):
        need = sum(e.lh + LANE_PAD for e in lst) + 2 * LANE_PAD
        if body[k].kind == "state" and body[k].h < need:
            body[k].h = need

    flat_pair = {(e.i, e.j): e for e in by_kind.get("flat", [])}
    top_lanes = {l: [] for l in order}
    bot_lanes = {l: [] for l in order}
    down_lanes = {l: [] for l in order}
    pairs = {}
    for e in by_kind.get("down", []):
        pairs.setdefault((e.i, e.j), []).append(e)
    for (i, j), lst in pairs.items():
        if len(lst) > 1 and (body[i].kind != "state"
                             or body[j].kind != "state"):
            for k, e in enumerate(lst):
                e.spline = (k, len(lst))
                e.t._props = SPLINE_PROPS

    lanes = {"top": top_lanes, "bot": bot_lanes, "down": down_lanes}
    for e in edges:
        if e.kind in lanes:
            lanes[e.kind][layer[id(body[e.i])]].append(e)

    flat_extra = {l: 0 for l in order}
    for e in by_kind.get("flat", []):
        l = layer[id(body[e.i])]
        flat_extra[l] = max(flat_extra[l], e.lh + 2 * LANE_PAD)

    init_up = {l: 0 for l in order}
    for iv in inits:
        for t in iv.trans:
            if t.kind == "external" and t.target:
                tg, _ = where[t.target]
                if id(tg) in idx:
                    l = layer[id(tg)]
                    init_up[l] = max(init_up[l], PSEUDO + INIT_UP + 20)
    child_lab = 0
    for v in body:
        for t in v.trans:
            if t.kind == "external" and t.target:
                tg, treg = where[t.target]
                if treg is not r and any(
                        tg in reg.vertices for reg in v.regions):
                    child_lab = max(child_lab, _lh(t) + 60)

    y = MARGIN
    first = order[0]
    y += max(init_up[first], _lane_h(top_lanes[first]), child_lab)
    row_y = {}
    for n, l in enumerate(order):
        rh = max(v.h for v in rows[l])
        row_y[l] = (y, rh)
        if n + 1 < len(order):
            nl = order[n + 1]
            g = _lane_h(down_lanes[l]) + _lane_h(bot_lanes[l]) + \
                max(_lane_h(top_lanes[nl]), init_up[nl])
            y += rh + max(g, GAP_MIN)
        else:
            y += rh + flat_extra[l] + _lane_h(bot_lanes[l])
    bottom_end = y

    row_gaps, row_w = {}, {}
    for l in order:
        row = rows[l]
        gx = []
        for a, b in zip(row, row[1:]):
            gap = GAP_X_MIN
            if (idx[id(a)], idx[id(b)]) in flat_pair or \
                    (idx[id(b)], idx[id(a)]) in flat_pair:
                gap = LABEL_W + 100
            gx.append(gap)
        row_gaps[l] = gx
        row_w[l] = sum(v.w for v in row) + sum(gx)
    maxw = max(row_w.values())

    back_groups, skip_groups = [], []
    for e in by_kind.get("back", []):
        if e.j not in back_groups:
            back_groups.append(e.j)
    for e in by_kind.get("skip", []):
        if e.j not in skip_groups:
            skip_groups.append(e.j)
    left_pad = 0
    if skip_groups:
        left_pad = LABEL_W + 80 + CH_STEP * len(skip_groups)
    if any(e.kind == "down" and len(
            [d for d in down_lanes[layer[id(body[e.i])]]
             if d.i == e.i and d.j == e.j]) > 1 for e in edges):
        left_pad = max(left_pad, LABEL_W + 40)

    for l in order:
        x = MARGIN + left_pad + (maxw - row_w[l]) // 2
        for k, v in enumerate(rows[l]):
            v.x = x
            v.y = row_y[l][0] + (row_y[l][1] - v.h) // 2
            x += v.w + (row_gaps[l][k] if k < len(row_gaps[l]) else 0)
    right_extent = max(v.x + v.w for v in body)
    left_extent = min(v.x for v in body)
    right_base = right_extent + LABEL_W + 60
    left_base = left_extent - LABEL_W - 60

    for iv in inits:
        tgt = tt = None
        for t in iv.trans:
            if t.kind == "external" and t.target:
                tg, _ = where[t.target]
                if id(tg) in idx:
                    tgt, tt = tg, t
        if tgt is None:
            continue
        ix = min(120, tgt.w // 4)
        iv.x = tgt.x + ix - PSEUDO // 2
        iv.y = tgt.y - PSEUDO - INIT_UP
        tt._src = iv
        tt._route = [(PSEUDO // 2, PSEUDO), (ix, 0)]
        tt._label = (PSEUDO + INIT_UP // 2 + 20, PSEUDO // 2 + 14,
                     PSEUDO // 2 + 214, PSEUDO + INIT_UP // 2 - 20)

    port = {}

    def add(v, side, e, end):
        port.setdefault((id(v), side), []).append((e, end))

    for e in edges:
        v, tg = body[e.i], body[e.j]
        if e.kind == "down" and not hasattr(e, "spline"):
            add(v, "b", e, "s")
            add(tg, "t", e, "t")
        elif e.kind == "flat":
            add(v, "r" if tg.x > v.x else "l", e, "s")
            add(tg, "l" if tg.x > v.x else "r", e, "t")
        elif e.kind == "top":
            add(v, "t", e, "s")
            add(tg, "t", e, "t")
        elif e.kind == "bot":
            add(v, "b", e, "s")
            add(tg, "b", e, "t")

    def other_x(e, end):
        o = body[e.j] if end == "s" else body[e.i]
        return o.x + o.w // 2

    byid = {id(b): b for b in body}
    off = {}
    for (vid, side), lst in port.items():
        v = byid[vid]
        lst.sort(key=lambda p: other_x(*p))
        size = v.w if side in "tb" else v.h
        for (e, end), o in zip(lst, _ports(len(lst), size)):
            off[(id(e), end)] = o

    lane_y = {}
    for l in order:
        ry, rh = row_y[l]
        cur = ry + rh + flat_extra[l]
        for e in down_lanes[l]:
            cur += LANE_PAD + e.lh
            lane_y[id(e)] = cur
        if down_lanes[l]:
            cur += LANE_PAD
        for e in bot_lanes[l]:
            cur += LANE_PAD
            lane_y[id(e)] = cur
            cur += e.lh
        cur = ry
        for e in top_lanes[l]:
            cur -= LANE_PAD + e.lh
            lane_y[id(e)] = cur + e.lh

    for e in edges:
        v, tg = body[e.i], body[e.j]
        so = off.get((id(e), "s"), 0)
        to = off.get((id(e), "t"), 0)
        if e.kind == "down" and hasattr(e, "spline"):
            k, n = e.spline
            sx = v.x + v.w // 2
            ty = tg.y
            sy = v.y + v.h
            bx = sx + int((k - (n - 1) / 2) * 2 * BULGE)
            by = (sy + ty) // 2
            ly = lane_y[id(e)]
            pts = [(sx, sy), (bx, by), (sx, ty)]
            if bx < sx:
                lab = (bx - 14 - LABEL_W, by - e.lh // 2)
            else:
                lab = (bx + 14, by - e.lh // 2)
            _finish(e, v, tg, pts, lab)
        elif e.kind == "down":
            sx = v.x + v.w // 2 + so
            tx = tg.x + tg.w // 2 + to
            ly = lane_y[id(e)]
            sy, ty = v.y + v.h, tg.y
            if sx == tx:
                pts = [(sx, sy), (tx, ty)]
                lab = (sx + 14, ly - e.lh)
            else:
                pts = [(sx, sy), (sx, ly), (tx, ly), (tx, ty)]
                lab = (min(sx, tx) + 14, ly - e.lh - 4)
            if so < 0:
                lab = (sx - 14 - LABEL_W, lab[1])
            _finish(e, v, tg, pts, lab)
        elif e.kind == "flat":
            if tg.x > v.x:
                sx, tx = v.x + v.w, tg.x
            else:
                sx, tx = v.x, tg.x + tg.w
            sy = v.y + v.h // 2 + so
            ty = tg.y + tg.h // 2 + to
            if sy == ty:
                pts = [(sx, sy), (tx, ty)]
            else:
                mx = (sx + tx) // 2
                pts = [(sx, sy), (mx, sy), (mx, ty), (tx, ty)]
            _finish(e, v, tg, pts, (min(sx, tx) + 20, sy + 8))
        elif e.kind == "bot":
            sx = v.x + v.w // 2 + so
            tx = tg.x + tg.w // 2 + to
            ly = lane_y[id(e)]
            pts = [(sx, v.y + v.h), (sx, ly), (tx, ly), (tx, tg.y + tg.h)]
            _finish(e, v, tg, pts, (min(sx, tx) + 20, ly + 6))
        elif e.kind == "top":
            sx = v.x + v.w // 2 + so
            tx = tg.x + tg.w // 2 + to
            ly = lane_y[id(e)]
            pts = [(sx, v.y), (sx, ly), (tx, ly), (tx, tg.y)]
            _finish(e, v, tg, pts, (min(sx, tx) + 20, ly - e.lh - 2))

    def ch_x(groups, g, base, sign):
        srt = sorted(groups, key=lambda j: layer[id(body[j])])
        return base + sign * (len(groups) - 1 - srt.index(g)) * CH_STEP

    for kind, groups, base, sign in (("back", back_groups, right_base, 1),
                                     ("skip", skip_groups, left_base, -1)):
        members_all = by_kind.get(kind, [])
        stubs = right_stub if sign > 0 else left_stub
        for g in groups:
            tg = body[g]
            cx = ch_x(groups, g, base, sign)
            ty = tg.y + tg.h // 2
            for e in [m for m in members_all if m.j == g]:
                v = body[e.i]
                lst = stubs[e.i]
                k = lst.index(e)
                if v.kind == "state":
                    sy = int(v.y + v.h / (len(lst) + 1) * (k + 1))
                else:
                    sy = v.y + v.h // 2 + sum(
                        m.lh + LANE_PAD for m in lst[:k])
                sx = v.x + v.w if sign > 0 else v.x
                tx = tg.x + tg.w if sign > 0 else tg.x
                pts = [(sx, sy), (cx, sy), (cx, ty), (tx, ty)]
                lab = (sx + 16, sy - e.lh - 4) if sign > 0 else \
                    (sx - 16 - LABEL_W, sy - e.lh - 4)
                _finish(e, v, tg, pts, lab)

    for e in by_kind.get("self", []):
        v = body[e.i]
        sx = v.x + v.w
        y1, y2 = v.y + v.h // 3, v.y + 2 * v.h // 3
        pts = [(sx, y1), (sx + 120, y1), (sx + 120, y2), (sx, y2)]
        _finish(e, v, v, pts, (sx + 140, y1 - 10))

    xmax = right_extent + (120 if by_kind.get("self") else 0)
    if back_groups:
        xmax = max(xmax, right_base + CH_STEP * len(back_groups))
    for e in edges:
        t = e.t
        xmax = max(xmax, t._src.x + t._label[2])
    r.w = xmax + MARGIN
    r.h = bottom_end + MARGIN
    for iv in inits:
        r.h = max(r.h, iv.y + iv.h + MARGIN)


def _finish(e, v, tg, pts, lab):
    """pts и lab (левый верхний угол подписи) — абсолютные в системе
    региона; переводит в соглашения Designer."""
    rel = []
    for n, (x, y) in enumerate(pts):
        if n == len(pts) - 1:
            rel.append((x - tg.x, y - tg.y))
        else:
            rel.append((x - v.x, y - v.y))
    e.t._src = v
    e.t._route = rel
    lx, ly = lab
    left = lx - v.x
    top = ly - v.y
    e.t._label = (top + e.lh, left, left + LABEL_W, top)


def _layers(nodes, edges):
    real = [i for i, v in enumerate(nodes) if v.kind == "state"]
    indeg = dict.fromkeys(real, 0)
    outdeg = dict.fromkeys(real, 0)
    for i, j, _t in edges:
        if i in outdeg and j in indeg:
            outdeg[i] += 1
            indeg[j] += 1
    ring = len(real) >= 3 and len(real) == len(nodes) and all(
        outdeg.get(i) == 1 and indeg.get(i) == 1 for i in real)
    if ring:
        nxt = {}
        for i, j, _t in edges:
            nxt[i] = j
        seq, cur, seen = [], real[0], set()
        while cur is not None and cur not in seen:
            seq.append(cur)
            seen.add(cur)
            cur = nxt.get(cur)
        if seq and nxt.get(seq[-1]) == seq[0]:
            for i, j, t in edges:
                if i == seq[-1] and j == seq[0]:
                    t._ring_wrap = True
        for k, i in enumerate(seq):
            nodes[i]._ord = k
        return {id(v): 0 for v in nodes}
    back = set()
    color = {}

    def dfs(u):
        color[u] = 1
        for i, j, _t in edges:
            if i != u:
                continue
            if color.get(j) == 1:
                back.add((i, j))
            elif color.get(j, 0) == 0:
                dfs(j)
        color[u] = 2
    for i in range(len(nodes)):
        if color.get(i, 0) == 0:
            dfs(i)
    fwd = [(i, j) for i, j, _t in edges if (i, j) not in back and i != j]
    preds = {i: [] for i in range(len(nodes))}
    for i, j in fwd:
        preds[j].append(i)
    layer = {}

    def lay(u):
        if u not in layer:
            layer[u] = 0 if not preds[u] else \
                max(lay(p) for p in preds[u]) + 1
        return layer[u]
    for i in range(len(nodes)):
        lay(i)
    by_layer = {}
    for i in range(len(nodes)):
        by_layer.setdefault(layer[i], []).append(i)
    order = {i: k for l in by_layer for k, i in enumerate(sorted(by_layer[l]))}
    for _ in range(4):
        for l in sorted(by_layer):
            ids = by_layer[l]
            ln = l + 1 if l + 1 in by_layer else l - 1
            if ln not in by_layer:
                continue

            def bary(i):
                nb = [order[j] for a, j in fwd
                      if a == i and layer.get(j) == ln] + \
                     [order[j] for a, j in fwd
                      if j == i and layer.get(a) == ln]
                return sum(nb) / len(nb) if nb else order[i]
            for k, i in enumerate(sorted(ids, key=bary)):
                order[i] = k
    rank = sorted(range(len(nodes)), key=lambda i: (layer[i], order[i]))
    for r_, i in enumerate(rank):
        layer[i] = r_
        nodes[i]._ord = 0
    return {id(nodes[i]): layer[i] for i in range(len(nodes))}


def _route_cross(v, tg, t):
    """Межрегиональный переход — двухточечный. Цель вложена в источник:
    падение через верхнюю грань над центром цели, подпись над целью."""
    h = _lh(t)
    t._src = v
    inside = any(u is tg for reg in v.regions for u in reg.vertices)
    if inside:
        p1x = INTERIOR_X + tg.x + tg.w // 2
        pts = [(p1x, 0), (tg.w // 2, 0)]
        top = INTERIOR_Y + tg.y - h - 12
        left = p1x + 14
        return pts, (top + h, left, left + LABEL_W, top)
    pts = [(v.w // 2, v.h), (tg.w // 2, 0)]
    my = (v.y + v.h + tg.y) // 2 - v.y
    left = v.w // 2 + 14
    return pts, (my + h // 2, left, left + LABEL_W, my - h // 2)
