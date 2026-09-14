#!/usr/bin/env python3

import argparse
import html


def block_pair(value):
    parts = value.split(',')
    if len(parts) != 2:
        raise argparse.ArgumentTypeError('expected I,J')

    try:
        i, j = (int(part) for part in parts)
    except ValueError as err:
        raise argparse.ArgumentTypeError('block dimensions must be integers') from err

    if i <= 0 or j <= 0:
        raise argparse.ArgumentTypeError('block dimensions must be positive')

    return i, j


def write_svg(args):
    block_i, block_j = args.block
    if args.n % block_i or args.n % block_j:
        raise SystemExit('--n must be divisible by both block dimensions')

    grid_size = args.n * args.cell
    block_width = block_i * args.cell
    block_height = block_j * args.cell
    active_size = args.cell - 2 * args.pad
    view_width = args.margin_left + grid_size + args.gap + args.info_width
    view_height = max(args.margin_top + grid_size + args.margin_bottom, args.height)

    label = html.escape(args.label)
    code = html.escape(args.code)

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_width:g} {view_height:g}" role="img" aria-labelledby="title desc">
  <title id="title">Animated {args.n} by {args.n} block loop</title>
  <desc id="desc">A highlighted point scans through a {args.n} by {args.n} grid in {block_i} by {block_j} blocks.</desc>
  <defs>
    <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <linearGradient id="blockFill" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#42affa" stop-opacity="0.18"/>
      <stop offset="1" stop-color="#f3a626" stop-opacity="0.12"/>
    </linearGradient>
  </defs>
  <style>
    .grid-bg {{ fill: #fff; }}
    .frame {{ fill: none; stroke: rgba(37,50,95,0.35); stroke-width: 1.4; }}
    .grid-line {{ stroke: rgba(37,50,95,0.34); stroke-width: 0.55; shape-rendering: crispEdges; }}
    .cell {{ fill: rgba(37,50,95,0.18); }}
    .visited {{ fill: rgba(0,86,179,0.72); }}
    .active {{ fill: #f3a626; filter: url(#glow); }}
    .block-fill {{ fill: url(#blockFill); }}
    .block-stroke {{ fill: none; stroke: #42affa; stroke-width: 2.4; stroke-linejoin: round; }}
    .label {{ fill: rgba(255,255,255,0.82); font: 600 17px Source Sans Pro, Liberation Sans, Arial, sans-serif; }}
    .small {{ fill: rgba(255,255,255,0.64); font: 13px Source Sans Pro, Liberation Sans, Arial, sans-serif; }}
    .code {{ fill: #d6f0ff; font: 15px ui-monospace, SFMono-Regular, Menlo, Consolas, Liberation Mono, monospace; }}
    .accent {{ fill: #f3a626; }}
  </style>
  <g transform="translate({args.margin_left:g} {args.margin_top:g})">
    <text class="label" x="0" y="-12">{label}</text>
    <rect class="grid-bg" x="0" y="0" width="{grid_size:g}" height="{grid_size:g}" rx="4"/>
    <rect class="frame" x="0" y="0" width="{grid_size:g}" height="{grid_size:g}" rx="4"/>
    <g id="cells"></g>
    <g id="grid"></g>
    <rect id="blockFillRect" class="block-fill" x="0" y="0" width="{block_width:g}" height="{block_height:g}" rx="2"/>
    <rect id="blockRect" class="block-stroke" x="0" y="0" width="{block_width:g}" height="{block_height:g}" rx="2"/>
    <rect id="activeCell" class="active" x="{args.pad:g}" y="{args.pad:g}" width="{active_size:g}" height="{active_size:g}" rx="1.5"/>
  </g>

  <g transform="translate({args.margin_left + grid_size + args.gap:g} {args.info_top:g})">
    <text class="small" x="0" y="0">block size</text>
    <text class="label" x="0" y="25"><tspan class="accent">{block_i}</tspan> x <tspan class="accent">{block_j}</tspan></text>
    <text class="small" x="0" y="68">outer loops</text>
    <text class="code" x="0" y="91">jsb, isb</text>
    <text class="small" x="0" y="134">inner kernel</text>
    <text class="code" x="0" y="157">{code}</text>
    <text class="code" x="0" y="179">  (k,jj,ii)</text>
  </g>

  <script><![CDATA[
    const n = {args.n};
    const blockI = {block_i};
    const blockJ = {block_j};
    const cell = {args.cell};
    const pad = {args.pad};
    const frameMs = {args.frame_ms};
    const holdFrames = {args.hold_frames};
    const cells = document.getElementById('cells');
    const grid = document.getElementById('grid');
    const active = document.getElementById('activeCell');
    const blockRect = document.getElementById('blockRect');
    const blockFill = document.getElementById('blockFillRect');
    const visited = [];

    for (let j = 0; j < n; j++) {{
      visited[j] = [];
      for (let i = 0; i < n; i++) {{
        const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        r.setAttribute('class', 'cell');
        r.setAttribute('x', i * cell + pad);
        r.setAttribute('y', j * cell + pad);
        r.setAttribute('width', cell - 2 * pad);
        r.setAttribute('height', cell - 2 * pad);
        r.setAttribute('rx', 1.2);
        cells.appendChild(r);
        visited[j][i] = r;
      }}
    }}

    for (let q = 1; q < n; q++) {{
      const v = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      v.setAttribute('class', 'grid-line');
      v.setAttribute('x1', q * cell);
      v.setAttribute('x2', q * cell);
      v.setAttribute('y1', 0);
      v.setAttribute('y2', n * cell);
      grid.appendChild(v);

      const h = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      h.setAttribute('class', 'grid-line');
      h.setAttribute('x1', 0);
      h.setAttribute('x2', n * cell);
      h.setAttribute('y1', q * cell);
      h.setAttribute('y2', q * cell);
      grid.appendChild(h);
    }}

    let step = 0;
    const stepsPerBlock = blockI * blockJ;
    const blocksPerRow = n / blockI;
    const blockRows = n / blockJ;
    const totalSteps = n * n + holdFrames;

    function clearVisited() {{
      for (let j = 0; j < n; j++) {{
        for (let i = 0; i < n; i++) visited[j][i].classList.remove('visited');
      }}
    }}

    function draw() {{
      if (step >= n * n) {{
        step++;
        if (step >= totalSteps) {{
          clearVisited();
          step = 0;
        }}
        return;
      }}

      const blockIndex = Math.floor(step / stepsPerBlock);
      const local = step % stepsPerBlock;
      const blockCol = blockIndex % blocksPerRow;
      const blockRow = Math.floor(blockIndex / blocksPerRow) % blockRows;
      const ii = local % blockI;
      const jj = Math.floor(local / blockI);
      const i = blockCol * blockI + ii;
      const j = blockRow * blockJ + jj;
      const bx = blockCol * blockI * cell;
      const by = blockRow * blockJ * cell;

      blockRect.setAttribute('x', bx);
      blockRect.setAttribute('y', by);
      blockFill.setAttribute('x', bx);
      blockFill.setAttribute('y', by);
      active.setAttribute('x', i * cell + pad);
      active.setAttribute('y', j * cell + pad);
      visited[j][i].classList.add('visited');
      step++;
    }}

    draw();
    setInterval(draw, frameMs);
  ]]></script>
</svg>
'''

    with open(args.output, 'w', encoding='utf-8') as svg_file:
        svg_file.write(svg)


def main():
    parser = argparse.ArgumentParser(description='Generate the animated block-loop title SVG.')
    parser.add_argument('-o', '--output', default='img/block_loop_title.svg')
    parser.add_argument('--n', type=int, default=32, help='grid dimension')
    parser.add_argument('--block', type=block_pair, default=(8, 2), help='block dimensions as I,J')
    parser.add_argument('--cell', type=float, default=10.0, help='cell size in SVG units')
    parser.add_argument('--pad', type=float, default=1.5, help='cell inset in SVG units')
    parser.add_argument('--frame-ms', type=int, default=32, help='animation frame interval')
    parser.add_argument('--hold-frames', type=int, default=10, help='pause before restarting')
    parser.add_argument('--label', default='runtime block decomposition')
    parser.add_argument('--code', default='do concurrent')
    parser.add_argument('--margin-left', type=float, default=40.0)
    parser.add_argument('--margin-top', type=float, default=34.0)
    parser.add_argument('--margin-bottom', type=float, default=66.0)
    parser.add_argument('--gap', type=float, default=26.0)
    parser.add_argument('--info-width', type=float, default=134.0)
    parser.add_argument('--info-top', type=float, default=96.0)
    parser.add_argument('--height', type=float, default=420.0)
    args = parser.parse_args()

    if args.n <= 0:
        parser.error('--n must be positive')
    if args.cell <= 0:
        parser.error('--cell must be positive')
    if args.pad < 0 or 2 * args.pad >= args.cell:
        parser.error('--pad must be nonnegative and smaller than half the cell size')
    if args.frame_ms <= 0:
        parser.error('--frame-ms must be positive')
    if args.hold_frames < 0:
        parser.error('--hold-frames must be nonnegative')

    write_svg(args)


if __name__ == '__main__':
    main()
