#!/usr/bin/env python3

import os
import sys

import argparse
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.rcParams.update({
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'font.family': 'sans-serif',
    'font.sans-serif': ['Source Sans Pro', 'Liberation Sans', 'Nimbus Sans', 'Arial', 'Helvetica'],
    'mathtext.fontset': 'stix',
    'font.size': 8,
    'axes.titlesize': 8,
    'axes.labelsize': 8,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'figure.titlesize': 9,
    'lines.linewidth': 1.0,
    'lines.markersize': 3.5,
})

CPU_cores = 96
#CPU_cores = 64
#CPU_cores = 0
REFERENCE_CONFIG = 96
force_origin = False
dark_bg = False
use_log_plot = True


# Standard modules
regions = [
    '(Ocean Coriolis & mom advection)',
    '(Ocean horizontal viscosity)',
    '(Ocean vertical viscosity)',
    '(Ocean continuity equation)',
    '(Ocean pressure force)',
    '(Ocean barotropic mode stepping)',
    #
    #'Ocean dynamics',
    #'Main loop',
    #'Ocean Other',
]

region_display_names = {
    '(Ocean Coriolis & mom advection)': 'Advection/Coriolis',
    '(Ocean horizontal viscosity)': 'Horizontal viscosity',
    '(Ocean vertical viscosity)': 'Vertical viscosity',
    '(Ocean continuity equation)': 'Continuity',
    '(Ocean pressure force)': 'Pressure force',
    '(Ocean barotropic mode stepping)': 'Barotropic mode',
}

## MPI scaling
#regions = [
#    '(Ocean Coriolis & mom advection)',
#    '(Ocean BT stepping calcs only)',
#    '(Ocean continuity equation)',
#    '(Ocean message passing)',
#    '(Ocean pressure force)',
#    '(Ocean vertical viscosity)',
#]


# Custom ranges
plt_yrange = {
#    '(Ocean continuity equation)': [0.0, 100.],
#    '(Ocean barotropic mode stepping)': [0.0, 30.],
}


plt.rcParams['axes.prop_cycle'] = plt.cycler(color=plt.cm.tab10.colors)


def region_display_name(region):
    return region_display_names.get(region, region)

# Create a square-like m x n pair
def square_pad(k):
    if k <= 0:
        raise ValueError("k must be positive")

    # ceil sqrt without using sqrt()
    n = 1
    while n * n < k:
        n += 1

    m = (k + n - 1) // n  # ceil(k/n)

    if m > n:
        m, n = n, m

    return m, n


def get_stats(platforms):
    stats = {}

    run_files = {
        expt: [
            os.path.join(expt, run)
            for run in os.listdir(expt)
            if run.endswith('.out') or run.endswith('.txt')
        ]
        for expt in platforms
    }

    for expt in platforms:
        data_files = run_files[expt]

        # NOTE: File is `(platform, resolution): region: timing`
        #   We invert to `platform: region: resolution: timing`
        #   But we may want `platform: region: timing: resolution`

        # NOTE: extension doesn't matter; `.out` or `.txt` are OK
        for runfile in data_files:
            resolution = runfile.rsplit('_', 1)[1].split('.')[0].lstrip('0')

            metrics = {}
            with open(runfile) as stats_file:
                for line in stats_file:
                    if not line.strip().startswith('hits'):
                        continue

                    keys = line.split()
                    break

                for line in stats_file:
                    # Skip blank lines
                    if not line.strip():
                        continue

                    # Skip any trailing output
                    if line.strip().startswith('MPP_STACK high water mark'):
                        continue

                    rec = line.rsplit(maxsplit=len(keys))

                    clk = rec[0]
                    try:
                        metrics[clk][resolution] = {}
                    except KeyError:
                        metrics[clk] = {}
                        metrics[clk][resolution] = {}

                    for stat, value in zip(keys, rec[1:]):
                        metrics[clk][resolution][stat] = float(value)

            # Poor man's deepupdate()
            # Assumes that all levels exist if `expt` exists.
            try:
                for reg in metrics:
                    stats[expt][reg].update(metrics[reg])
            except KeyError:
                stats[expt] = metrics

    return stats


def add_cpu_arrows(ax, color):
    x_cpu = ax.transAxes.inverted().transform(
        ax.transData.transform((CPU_cores, ax.get_ylim()[0]))
    )[0]
    x_cpu = min(max(x_cpu, 0.05), 0.95)

    left_x = 0.04
    right_x = 0.96
    left_y = 0.65
    right_y = 0.12

    ax.annotate(
        '',
        xy=(left_x, left_y), xycoords='axes fraction',
        xytext=(x_cpu, left_y), textcoords='axes fraction',
        arrowprops={'arrowstyle': '<->', 'color': color, 'linewidth': 0.8},
        annotation_clip=False,
    )
    ax.text(
        (left_x + x_cpu) / 2, left_y, 'weak CPU scaling',
        transform=ax.transAxes, color=color, ha='center', va='center',
        fontsize='small', backgroundcolor=ax.get_facecolor(),
    )

    ax.annotate(
        '',
        xy=(right_x, right_y), xycoords='axes fraction',
        xytext=(x_cpu, right_y), textcoords='axes fraction',
        arrowprops={'arrowstyle': '<->', 'color': color, 'linewidth': 0.8},
        annotation_clip=False,
    )
    ax.text(
        (x_cpu + right_x) / 2, right_y, 'fixed CPUs',
        transform=ax.transAxes, color=color, ha='center', va='center',
        fontsize='small', backgroundcolor=ax.get_facecolor(),
    )


def timing_series(stats, expt, reg):
    nx_keys = stats[expt][reg].keys()
    nx = [int(k.rstrip('x')) for k in nx_keys]

    nx_keys = [x for _, x in sorted(zip(nx, nx_keys))]
    nx.sort()

    tavg = 1000. * np.array([stats[expt][reg][nx]['tavg'] for nx in nx_keys])
    hits = np.array(
        [stats[expt]['Ocean dynamics'][nx]['hits'] for nx in nx_keys]
    ) / 2.

    return nx, tavg / hits


def filter_min_config(nx, values, min_config):
    if min_config is None:
        return nx, values

    nx_array = np.array(nx)
    keep = nx_array >= min_config
    return list(nx_array[keep]), values[keep]


def config_tick_labels(nx, xscale_factor):
    labels = []
    for x in nx:
        scaled = x / xscale_factor
        label = f'{scaled:g}' if scaled % 1 else f'{int(scaled)}'
        labels.append(f'{label}x')

    return labels


def style_dark_axes(ax, text_color):
    if not dark_bg:
        return

    ax.set_facecolor('white')


def style_legend(legend):
    return


def set_log2_timing_ticks(ax):
    """Use 2x log ticks/grid lines, labeling every 4x from the top tick."""

    def label_every_four_and_top(v, pos):
        if v <= 0:
            return ''

        exponent = np.log2(v)
        rounded = round(exponent)
        if not np.isclose(exponent, rounded):
            return ''

        top_exponent = round(np.floor(np.log2(ax.get_ylim()[1])))
        if (top_exponent - rounded) % 2:
            return ''

        return f'{v:g}'

    ax.yaxis.set_major_locator(mticker.LogLocator(base=2, subs=(1.0,), numticks=100))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(label_every_four_and_top))
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    ax.grid(True, axis='y', which='major', linestyle=':', linewidth=0.5, alpha=1.0)


def plot_speedup(platforms, regions, stats, output, legend_labels, figsize,
                 title, min_config, xscale_factor):
    if len(platforms) != 2:
        raise ValueError('--speedup requires exactly two platform directories')

    nplot = len(regions)
    nrow, ncol = square_pad(nplot)
    fig, axes = plt.subplots(nrow, ncol, figsize=figsize, squeeze=False,
            constrained_layout=True)

    if dark_bg:
        fig.patch.set_facecolor('none')
        ctxt = 'white'
    else:
        ctxt = 'black'

    fig.suptitle(title, color=ctxt)

    cpu, gpu = platforms
    cpu_label = legend_labels.get(cpu, os.path.basename(os.path.normpath(cpu)))
    gpu_label = legend_labels.get(gpu, os.path.basename(os.path.normpath(gpu)))

    for reg, ax in zip(regions, axes.flat):
        cpu_x, cpu_t = timing_series(stats, cpu, reg)
        gpu_x, gpu_t = timing_series(stats, gpu, reg)
        cpu_x, cpu_t = filter_min_config(cpu_x, cpu_t, min_config)
        gpu_x, gpu_t = filter_min_config(gpu_x, gpu_t, min_config)
        common = sorted(set(cpu_x).intersection(gpu_x))

        cpu_map = dict(zip(cpu_x, cpu_t))
        gpu_map = dict(zip(gpu_x, gpu_t))
        speedup = np.array([cpu_map[x] / gpu_map[x] for x in common])

        ax.set_title(region_display_name(reg), color=ctxt)
        style_dark_axes(ax, ctxt)
        ax.set_xscale('log')
        ax.xaxis.set_major_locator(mticker.FixedLocator(common))
        ax.xaxis.set_minor_locator(mticker.NullLocator())
        ax.set_xticklabels(config_tick_labels(common, xscale_factor), rotation=45)
        ax.axhline(1.0, linestyle=':', color='0.5', linewidth=0.8)
        ax.grid(True, linestyle=':', linewidth=0.5, alpha=1.0)
        ax.tick_params(colors=ctxt)
        ax.set_ylabel(f'{cpu_label} / {gpu_label}', color=ctxt)

        line, = ax.plot(common, speedup, '-o', label='speedup')
        ax.fill_between(common, 1.0, speedup, alpha=0.08, color=line.get_color())

    plt.savefig(output)


def plot_timing_with_speedup(platforms, regions, stats, output, legend_labels,
                             figsize, title, min_config, xscale_factor,
                             cpu_arrows):
    if len(platforms) != 2:
        raise ValueError('--with-speedup requires exactly two platform directories')
    if len(regions) != 1:
        raise ValueError('--with-speedup currently requires exactly one timing region')

    if dark_bg:
        facecolor = 'none'
        ctxt = 'white'
    else:
        facecolor = 'white'
        ctxt = 'black'

    fig, (ax_time, ax_speedup) = plt.subplots(
        2, 1, figsize=figsize, constrained_layout=True,
        gridspec_kw={'height_ratios': [2, 1]}, sharex=True,
    )
    fig.patch.set_facecolor(facecolor)
    ax_time.set_title(title, color=ctxt)
    style_dark_axes(ax_time, ctxt)
    style_dark_axes(ax_speedup, ctxt)

    region = regions[0]
    cpu, gpu = platforms
    cpu_label = legend_labels.get(cpu, os.path.basename(os.path.normpath(cpu)))
    gpu_label = legend_labels.get(gpu, os.path.basename(os.path.normpath(gpu)))

    cpu_x, cpu_t = timing_series(stats, cpu, region)
    gpu_x, gpu_t = timing_series(stats, gpu, region)
    cpu_x, cpu_t = filter_min_config(cpu_x, cpu_t, min_config)
    gpu_x, gpu_t = filter_min_config(gpu_x, gpu_t, min_config)
    common = sorted(set(cpu_x).intersection(gpu_x))
    cpu_map = dict(zip(cpu_x, cpu_t))
    gpu_map = dict(zip(gpu_x, gpu_t))
    speedup = np.array([cpu_map[x] / gpu_map[x] for x in common])

    colors = plt.cm.tab10.colors
    ax_time.plot(cpu_x, cpu_t, '-o', label=cpu_label, color=colors[0])
    ax_time.plot(gpu_x, gpu_t, '-o', label=gpu_label, color=colors[1])
    ax_time.set_xscale('log')
    ax_time.set_yscale('log')
    set_log2_timing_ticks(ax_time)
    ax_time.set_ylabel('Time per step (ms)', color=ctxt)
    ax_time.grid(True, linestyle=':', linewidth=0.5, alpha=1.0)
    ax_time.tick_params(colors=ctxt)
    style_legend(ax_time.legend())
    if cpu_arrows:
        add_cpu_arrows(ax_time, colors[0])

    for ax in (ax_time, ax_speedup):
        ax.axvline(REFERENCE_CONFIG, linestyle=':', color='0.35', linewidth=1.0)

    ax_speedup.plot(common, speedup, '-o', color=colors[2])
    ax_speedup.set_ylim(0.25, 3.25)
    ax_speedup.axhline(1.0, linestyle='--', color='0.25', linewidth=1.0)
    ax_speedup.set_xscale('log')
    ax_speedup.set_ylabel('GPU speedup', color=ctxt)
    if xscale_factor == 4:
        xlabel = r'Horizontal domain scale (1x = $64 \times 64$ cells)'
    else:
        xlabel = r'Horizontal domain scale (1x = $32 \times 32$ cells)'
    ax_speedup.set_xlabel(xlabel, color=ctxt)
    ax_speedup.yaxis.set_major_locator(mticker.FixedLocator([1, 2, 3]))
    ax_speedup.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, pos: f'{v:g}x' if v > 0 else '0')
    )
    ax_speedup.grid(True, linestyle=':', linewidth=0.5, alpha=1.0)
    ax_speedup.tick_params(colors=ctxt)

    ax_speedup.xaxis.set_major_locator(mticker.FixedLocator(common))
    ax_speedup.xaxis.set_minor_locator(mticker.NullLocator())
    ax_speedup.set_xticklabels(config_tick_labels(common, xscale_factor), rotation=45)

    plt.savefig(output)


def plot_results(platforms, regions, stats, output, legend_labels, yrange,
                 shared_yrange, figsize, cpu_arrows, title, min_config,
                 xscale_factor):
    nplot = len(regions)
    nrow, ncol = square_pad(nplot)
    yvalues = []

    # Plot results
    fig, axes = plt.subplots(nrow, ncol, figsize=figsize, squeeze=False,
    #fig, axes = plt.subplots(nrow, ncol, figsize=(8, 4), squeeze=False,
            constrained_layout=True)

    if dark_bg:
        fig.patch.set_facecolor('none')
        ctxt = 'white'
    else:
        ctxt = 'black'

    fig.suptitle(title, color=ctxt)
    #fig.suptitle(f'Runtime per step (ms) for MOM6 modules from 32×32 to 128×128')

    colors = plt.cm.tab10.colors[:len(platforms)]

    for expt in platforms:
        for reg, ax in zip(regions, axes.flat):
            # Fetch metric keys
            nx_keys = stats[expt][reg].keys()
            nx = [int(k.rstrip('x')) for k in nx_keys]

            # Re-sort from 1x to max
            nx_keys = [x for _, x in sorted(zip(nx, nx_keys))]
            nx.sort()

            if min_config is not None:
                nx_keys = [key for key in nx_keys if int(key.rstrip('x')) >= min_config]
                nx = [int(key.rstrip('x')) for key in nx_keys]

            tmin = 1000. * np.array([stats[expt][reg][nx]['tmin'] for nx in nx_keys])
            tmax = 1000. * np.array([stats[expt][reg][nx]['tmax'] for nx in nx_keys])
            tavg = 1000. * np.array([stats[expt][reg][nx]['tavg'] for nx in nx_keys])

            # There are two clocks per dycore loop, but this could change.
            hits = np.array(
                    [stats[expt]['Ocean dynamics'][nx]['hits'] for nx in nx_keys]
            ) / 2.

            ax.set_title(region_display_name(reg), color=ctxt)
            style_dark_axes(ax, ctxt)

            # Explicit log ticks
            if (use_log_plot):
                ax.set_xscale('log')
                ax.xaxis.set_major_locator(mticker.FixedLocator(nx))
                ax.xaxis.set_minor_locator(mticker.NullLocator())
                ax.set_xticklabels(config_tick_labels(nx, xscale_factor), rotation=45)

                ax.set_yscale('log')
                set_log2_timing_ticks(ax)

            ax.tick_params(colors=ctxt)

            ax.grid(True, linestyle=':', linewidth=0.5, alpha=1.0)

            if any(tavg != tmin) or any(tavg != tmax):
                ax.fill_between(nx, tmin / hits, tmax / hits,
                                alpha=0.15, linewidth=0)

            label = legend_labels.get(expt, os.path.basename(os.path.normpath(expt)))

            line, = ax.plot(nx, tavg / hits, '-', label=label)

            col = line.get_color()

            ax.plot(nx, tavg / hits, 'o', color=col)

            yvalues.extend(tmin / hits)
            yvalues.extend(tmax / hits)
            yvalues.extend(tavg / hits)

            if not yrange and not shared_yrange and reg in plt_yrange:
                ax.set_ylim(plt_yrange[reg])

    #axes[1,2].set_ylim([0.0, 0.008])

    # Force origin in plots
    # Per-plot?
    if force_origin:
        for ax in axes.flat:
            ax.set_ylim([0, None])

    if yrange:
        for ax in axes.flat:
            ax.set_ylim(yrange)
    elif shared_yrange and yvalues:
        ymin = min(y for y in yvalues if y > 0) if use_log_plot else min(yvalues)
        ymax = max(yvalues)
        for ax in axes.flat:
            ax.set_ylim(ymin, ymax)

    if CPU_cores > 0 and cpu_arrows:
        for ax in axes.flat:
            add_cpu_arrows(ax, plt.cm.tab10.colors[0])

    style_legend(axes[0, 0].legend())

    plt.savefig(output)


def main():
    global dark_bg

    p = argparse.ArgumentParser()
    p.add_argument('platforms', nargs='+', help='Platform directories, e.g. a100 h100')
    p.add_argument('-o', '--output', default='out.svg', metavar='FILE', help='output filename')
    p.add_argument(
        '-l', '--label', default='', metavar='LABEL[,LABEL...]',
        help='comma-separated legend labels, matched to platform order'
    )
    p.add_argument(
        '-y', '--yrange', default='', metavar='MIN,MAX',
        help='fixed y-axis range for all plots, e.g. 0.1,100'
    )
    p.add_argument(
        '--shared-yrange', action='store_true',
        help='use one computed y-axis range for all plots'
    )
    p.add_argument(
        '--dark', action='store_true',
        help='use dark-background plot text colors'
    )
    p.add_argument(
        '--figsize', default='12,6', metavar='WIDTH,HEIGHT',
        help='figure size in inches, e.g. 14,8'
    )
    p.add_argument(
        '--cpu-arrows', action='store_true',
        help='add weak/fixed CPU scaling arrows around the CPU dashed line'
    )
    p.add_argument(
        '--min-config', type=int, default=None, metavar='N',
        help='omit horizontal domain scale factors smaller than N'
    )
    p.add_argument(
        '--xscale-factor', type=float, default=1.0, metavar='N',
        help='divide displayed horizontal domain scale labels by N'
    )
    p.add_argument(
        '--regions', default='', metavar='REGION[,REGION...]',
        help='comma-separated timing regions to plot'
    )
    p.add_argument(
        '--title', default='Time per step (ms) from 32×32 to 1024×1024',
        help='figure title'
    )
    p.add_argument(
        '--speedup', action='store_true',
        help='plot first platform divided by second platform instead of timings'
    )
    p.add_argument(
        '--with-speedup', action='store_true',
        help='plot timing and first-platform/second-platform speedup panels'
    )
    args = p.parse_args()

    dark_bg = args.dark

    platforms = args.platforms
    labels = next(csv.reader([args.label])) if args.label else []
    if len(labels) > len(platforms):
        p.error('more labels provided than platform directories')

    legend_labels = dict(zip(platforms, labels))

    figsize = [float(v) for v in next(csv.reader([args.figsize]))]
    if len(figsize) != 2:
        p.error('--figsize must have exactly two values: WIDTH,HEIGHT')

    yrange = None
    if args.yrange:
        yrange = [float(v) for v in next(csv.reader([args.yrange]))]
        if len(yrange) != 2:
            p.error('--yrange must have exactly two values: MIN,MAX')
        if use_log_plot and yrange[0] <= 0:
            p.error('--yrange MIN must be positive for log plots')

    plot_regions = next(csv.reader([args.regions])) if args.regions else regions

    stats = get_stats(platforms)
    if args.speedup and args.with_speedup:
        p.error('--speedup and --with-speedup are mutually exclusive')

    if args.with_speedup:
        plot_timing_with_speedup(platforms, plot_regions, stats, args.output,
                                 legend_labels, figsize, args.title,
                                 args.min_config, args.xscale_factor,
                                 args.cpu_arrows)
    elif args.speedup:
        plot_speedup(platforms, plot_regions, stats, args.output, legend_labels,
                     figsize, args.title, args.min_config, args.xscale_factor)
    else:
        plot_results(platforms, plot_regions, stats, args.output, legend_labels,
                      yrange, args.shared_yrange, figsize, args.cpu_arrows,
                      args.title, args.min_config, args.xscale_factor)


if __name__ == '__main__':
    main()
