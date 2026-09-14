#!/usr/bin/env python3

import os
import sys

import argparse
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import re

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

#CPU_cores = 96
#CPU_cores = 64
CPU_cores = 0
force_origin = False
dark_bg = False
use_log_plot = True

quantities = {
    'time': 'Time per step (ms)',
    'speedup': 'Speedup',
    'efficiency': 'Scaling efficiency',
    'work-rate': 'Work per second',
    'work-rate-per-domain': 'Work per second per domain size',
}

config_display_labels = {
    '64': '256 × 256',
    '128': '512 × 256',
    '256': '512 × 512',
    '512': '1024 × 512',
    '1024': '1024 × 1024',
}


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


def p_value(expt):
    expt = os.path.basename(os.path.normpath(expt))
    match = re.search(r'(?:^|_)p(\d+)(?:_|$)', expt)
    if not match:
        raise ValueError(f"could not parse p value from directory name: {expt}")

    return int(match.group(1))


def config_value(config):
    return int(config.rstrip('x'))


def config_label(config):
    return f"{config_value(config)}x"


def config_display_label(config):
    return config_display_labels.get(config, config_label(config))


def style_dark_axes(ax, text_color):
    if not dark_bg:
        return

    ax.set_facecolor('white')


def style_legend(legend):
    return


def normalize_config(config):
    return str(config_value(config.strip()))


def quantity_values(quantity, config, px, tmin, tmax, tavg, hits):
    seconds_min = tmin / hits
    seconds_max = tmax / hits
    seconds_avg = tavg / hits

    if quantity == 'time':
        return 1000. * seconds_min, 1000. * seconds_max, 1000. * seconds_avg

    if quantity == 'speedup':
        baseline = seconds_avg[0]
        return baseline / seconds_max, baseline / seconds_min, baseline / seconds_avg

    if quantity == 'efficiency':
        baseline = seconds_avg[0]
        speedup_min = baseline / seconds_max
        speedup_max = baseline / seconds_min
        speedup_avg = baseline / seconds_avg
        ideal = np.array(px) / px[0]
        return speedup_min / ideal, speedup_max / ideal, speedup_avg / ideal

    # Config suffixes are area-scale factors: 001 -> 32x32, 004 -> 64x64,
    # 016 -> 128x128, etc. Work is therefore proportional to config, not config^2.
    work = config_value(config)
    if quantity == 'work-rate':
        return work / seconds_max, work / seconds_min, work / seconds_avg

    if quantity == 'work-rate-per-domain':
        domain_size = work / np.array(px)
        return (
            work / seconds_max / domain_size,
            work / seconds_min / domain_size,
            work / seconds_avg / domain_size,
        )

    raise ValueError(f"unknown quantity: {quantity}")


def perfect_scaling_values(quantity, px, y0):
    px = np.array(px)
    p0 = px[0]

    if quantity == 'time':
        return y0 * p0 / px

    if quantity in ('speedup', 'work-rate'):
        return y0 * px / p0

    if quantity == 'efficiency':
        return np.ones_like(px, dtype=float)

    if quantity == 'work-rate-per-domain':
        return np.full_like(px, y0, dtype=float)

    raise ValueError(f"unknown quantity: {quantity}")


def scaling_reference(quantity, px, y0, weak):
    if weak and quantity in ('speedup', 'efficiency'):
        return np.ones_like(np.array(px), dtype=float), 'ideal weak scaling'

    return perfect_scaling_values(quantity, px, y0), 'ideal scaling'


def offset_scaling_guide(quantity, guide, results):
    if quantity == 'efficiency':
        return guide

    if not results:
        return guide

    data = np.vstack(results)

    if quantity == 'time':
        target = 0.85 * np.min(data, axis=0)
        scale = np.min(target / guide)
        return guide * min(scale, 0.85)

    target = 1.25 * np.max(data, axis=0)
    scale = np.max(target / guide)
    return guide * max(scale, 1.25)


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


def plot_results(platforms, regions, stats, output, legend_labels, platform_labels, selected_configs, min_config, quantity, linear_y, figsize, weak, ylim):
    nplot = len(regions)
    nrow, ncol = square_pad(nplot)

    platforms = sorted(platforms, key=p_value)
    px = [p_value(expt) for expt in platforms]

    # Plot results
    fig, axes = plt.subplots(nrow, ncol, figsize=figsize, squeeze=False,
    #fig, axes = plt.subplots(nrow, ncol, figsize=(8, 4), squeeze=False,
            constrained_layout=True)

    if dark_bg:
        fig.patch.set_facecolor('none')
        ctxt = 'white'
    else:
        ctxt = 'black'

    fig.suptitle(f'{quantities[quantity]} vs number of GPUs for fixed domain', color=ctxt)
    #fig.suptitle(f'Runtime per step (ms) for MOM6 modules from 32×32 to 128×128')

    colors = plt.cm.tab10.colors[:len(platforms)]

    ## Denote the CPU core limit
    if CPU_cores > 0:
        for ax in axes.flat:
            ax.axvline(CPU_cores, linestyle="--", color=colors[0])
            #ax.axvline(2. * CPU_cores, linestyle="--", color=colors[1])
            #ax.axvline(96, linestyle="--", color=colors[1])

    for reg, ax in zip(regions, axes.flat):
        config_sets = [
            set(stats[expt][reg]) & set(stats[expt]['Ocean dynamics'])
            for expt in platforms
        ]
        configs = set.intersection(*config_sets)

        if selected_configs:
            configs = configs & set(selected_configs)

        if min_config:
            configs = [config for config in configs if config_value(config) >= min_config]

        configs = sorted(configs, key=config_value)

        if not configs:
            print(f"warning: no common configurations for {reg}", file=sys.stderr)
            continue

        ax.set_title(region_display_name(reg), color=ctxt)

        # Explicit log ticks
        if (use_log_plot):
            ax.set_xscale('log')
            ax.xaxis.set_major_locator(mticker.FixedLocator(px))
            ax.xaxis.set_minor_locator(mticker.NullLocator())
            ax.set_xticklabels(
                [platform_labels[expt] if expt in platform_labels else f"{p}" for expt, p in zip(platforms, px)],
            )

            if weak and quantity == 'speedup':
                ax.set_yscale('linear')
                ax.set_ylim(0, 1.2)
                ax.yaxis.set_major_locator(mticker.FixedLocator([0, 0.25, 0.5, 0.75, 1.0, 1.2]))
            elif quantity == 'efficiency':
                ax.set_ylim(0, 1.2)
                ax.yaxis.set_major_locator(mticker.FixedLocator([0, 0.25, 0.5, 0.75, 1.0, 1.2]))
            elif not linear_y:
                ax.set_yscale('log')
                ax.yaxis.set_major_formatter(
                    mticker.FuncFormatter(lambda v, pos: f"{v:g}")
                )
                ax.yaxis.set_major_locator(
                    #mticker.LogLocator(base=10, subs=(1.0, 2.0, 5.0))
                    mticker.LogLocator(base=2)
                )
                ax.yaxis.set_minor_locator(mticker.NullLocator())

        ax.tick_params(colors=ctxt)

        ax.grid(True, linestyle=':', linewidth=0.5, alpha=1.0)
        style_dark_axes(ax, ctxt)

        scaling_ref = None
        results = []

        for config in configs:
            tmin = np.array([stats[expt][reg][config]['tmin'] for expt in platforms])
            tmax = np.array([stats[expt][reg][config]['tmax'] for expt in platforms])
            tavg = np.array([stats[expt][reg][config]['tavg'] for expt in platforms])

            # There are two clocks per dycore loop, but this could change.
            hits = np.array(
                    [stats[expt]['Ocean dynamics'][config]['hits'] for expt in platforms]
            ) / 2.

            ymin, ymax, yavg = quantity_values(quantity, config, px, tmin, tmax, tavg, hits)

            if config == configs[-1]:
                scaling_ref = yavg[0]
            results.append(yavg)

            if any(yavg != ymin) or any(yavg != ymax):
                ax.fill_between(px, ymin, ymax,
                                alpha=0.15, linewidth=0)

            label = legend_labels[config] if config in legend_labels else config_display_label(config)

            line, = ax.plot(px, yavg, '-', label=label)

            col = line.get_color()

            ax.plot(px, yavg, 'o', color=col)

        perfect_y0 = 1.0 if quantity in ('speedup', 'efficiency') else scaling_ref
        perfect, perfect_label = scaling_reference(quantity, px, perfect_y0, weak)
        if quantity not in ('speedup', 'efficiency'):
            perfect = offset_scaling_guide(quantity, perfect, results)
        ax.plot(px, perfect, '--', color='k', alpha=0.6, label=perfect_label)

        #if reg in plt_yrange:
        #    ax.set_ylim(plt_yrange[reg])

    #axes[1,2].set_ylim([0.0, 0.008])

    # Force origin in plots
    # Per-plot?
    if force_origin:
        for ax in axes.flat:
            ax.set_ylim([0, None])

    if ylim:
        for ax in axes.flat:
            ax.set_ylim(ylim)

    style_legend(axes[0, 0].legend())

    plt.savefig(output)


def main():
    global dark_bg

    p = argparse.ArgumentParser()
    p.add_argument('platforms', nargs='+', help='Platform directories, e.g. a100 h100')
    p.add_argument('-o', '--output', default='out.svg', metavar='FILE', help='output filename')
    p.add_argument(
        '-l', '--label', default='', metavar='LABEL[,LABEL...]',
        help='comma-separated legend labels, matched to config order'
    )
    p.add_argument(
        '--platform-label', default='', metavar='LABEL[,LABEL...]',
        help='comma-separated x-axis labels, matched to numeric p order'
    )
    p.add_argument(
        '-c', '--configs', default='', metavar='CONFIG[,CONFIG...]',
        help='comma-separated configs to plot, e.g. 1x,2x,4x'
    )
    p.add_argument(
        '-m', '--min-config', default='', metavar='CONFIG',
        help='smallest config to plot, e.g. 64x'
    )
    p.add_argument(
        '-q', '--quantity', choices=quantities, default='speedup',
        help='y-axis quantity to plot'
    )
    p.add_argument(
        '--linear-y', action='store_true',
        help='use a linear y-axis instead of log scale'
    )
    p.add_argument(
        '--dark', action='store_true',
        help='use dark-background plot text colors'
    )
    p.add_argument(
        '--figsize', default='12,7', metavar='WIDTH,HEIGHT',
        help='figure size in inches, e.g. 14,8'
    )
    p.add_argument(
        '--weak', action='store_true',
        help='use weak-scaling reference line'
    )
    p.add_argument(
        '--ylim', default='', metavar='MIN,MAX',
        help='y-axis limits applied to all plots, e.g. 0,1.2'
    )
    args = p.parse_args()

    dark_bg = args.dark

    platforms = args.platforms
    labels = next(csv.reader([args.label])) if args.label else []
    platform_label_values = next(csv.reader([args.platform_label])) if args.platform_label else []
    selected_configs = [normalize_config(c) for c in next(csv.reader([args.configs]))] if args.configs else []
    min_config = config_value(normalize_config(args.min_config)) if args.min_config else None
    figsize = [float(v) for v in next(csv.reader([args.figsize]))]
    if len(figsize) != 2:
        p.error('--figsize must have exactly two values: WIDTH,HEIGHT')
    ylim = [float(v) for v in next(csv.reader([args.ylim]))] if args.ylim else None
    if ylim and len(ylim) != 2:
        p.error('--ylim must have exactly two values: MIN,MAX')
    sorted_platforms = sorted(platforms, key=p_value)
    if len(platform_label_values) > len(sorted_platforms):
        p.error('more platform labels provided than platform directories')
    if labels and not selected_configs:
        p.error('labels require --configs so config order is explicit')
    if selected_configs and len(labels) > len(selected_configs):
        p.error('more labels provided than selected configs')

    legend_labels = dict(zip(selected_configs, labels))
    platform_labels = dict(zip(sorted_platforms, platform_label_values))

    try:
        stats = get_stats(platforms)
        plot_results(platforms, regions, stats, args.output, legend_labels, platform_labels, selected_configs, min_config, args.quantity, args.linear_y, figsize, args.weak, ylim)
    except ValueError as err:
        p.error(str(err))


if __name__ == '__main__':
    main()
