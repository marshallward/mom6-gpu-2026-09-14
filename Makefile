THEME=gfdl
REPO=https://github.com/hakimel/reveal.js/archive/master.zip
REVEAL_SOURCE=../nrl2026/reveal.js
PYTHON=python
MPLBACKEND=Agg
PRESENTATION=mom6-gpu-2026-09-14
DEPLOY_DIR=public

SINGLE_DEVICE_CPU_RUN=runs/c6_96pe_avx512
DEVICE_GPU_RUN=runs/arm_20260809
H100_RUNS=runs/h100_p1_20260725 runs/h100_p2_20260725 runs/h100_p4_20260725 \
	runs/h100_p8_20260725 runs/h100_p10_20260725

ASYFILES=asy/block_shapes.asy
ASYFIGURES=$(patsubst %.asy,%.svg,$(subst asy/,img/,$(ASYFILES)))
RESULT_FIGURES=img/dycore_and_main.svg img/module_scaling.svg \
	img/module_speedup.svg img/dycore_speedup.svg
TITLE_FIGURE=img/block_loop_title.svg

FLAGS=-s \
	  -f rst -t revealjs \
	  --slide-level=2 \
	  -V revealjs-url=./reveal.js \
	  -V theme=$(THEME) \
	  -V slideNumber=true \
	  --template=gfdl.revealjs \
	  --no-highlight \
	  --mathjax

all: index.html


reveal.js/dist/reveal.js:
	rm -rf reveal.js
	@if [ -d "$(REVEAL_SOURCE)" ]; then \
		cp -a "$(REVEAL_SOURCE)" .; \
	else \
		wget -N $(REPO); \
		unzip master.zip; \
		mv reveal.js-master reveal.js; \
	fi

reveal.js/css/theme/gfdl.css: gfdl.css reveal.js/dist/reveal.js
	mkdir -p reveal.js/css/theme
	cp gfdl.css reveal.js/css/theme/

index.html: slides.txt Makefile gfdl.revealjs reveal.js/css/theme/gfdl.css assets/bg_gfdl.jpg $(TITLE_FIGURE) $(ASYFIGURES) $(RESULT_FIGURES)
	pandoc $(FLAGS) $< -o $@
	sed -i 's|data="<p>\([^<]*\)</p>"|data="\1"|g' $@
	sed -i 's|<p class="title-kicker"><p>\([^<]*\)</p></p>|<p class="title-kicker">\1</p>|g' $@
	sed -i 's/<li class="fragment"/<li/g' $@

img/block_loop_title.svg: scripts/gen_block_loop_title.py | img
	$(PYTHON) $< -o $@ --n 32 --block 8,4 --frame-ms 48

img/%.svg: asy/%.asy | img
	asy -f svg $< -o $(basename $@)

img/module_scaling.svg: runs/gen_plot.py $(SINGLE_DEVICE_CPU_RUN)/* $(DEVICE_GPU_RUN)/* | img
	MPLBACKEND=$(MPLBACKEND) $(PYTHON) $< \
		$(SINGLE_DEVICE_CPU_RUN) $(DEVICE_GPU_RUN) \
		-o $@ -l "AMD EPYC 9654,GH200" --figsize 9.0,4.8 \
		--min-config 4 \
		--xscale-factor 4 \
		--dark

img/dycore_and_main.svg: runs/gen_plot.py $(SINGLE_DEVICE_CPU_RUN)/* $(DEVICE_GPU_RUN)/* | img
	MPLBACKEND=$(MPLBACKEND) $(PYTHON) $< \
		$(SINGLE_DEVICE_CPU_RUN) $(DEVICE_GPU_RUN) \
		-o $@ -l "AMD EPYC 9654,GH200" --figsize 5.5,3.5 \
		--regions "Main loop" \
		--with-speedup \
		--min-config 4 \
		--xscale-factor 4 \
		--title "MOM6 timestep: socket-to-card comparison" \
		--dark

img/module_speedup.svg: runs/plot_module_scaling.py $(H100_RUNS:=/*) | img
	MPLBACKEND=$(MPLBACKEND) $(PYTHON) $< $(H100_RUNS) \
		-o $@ -q speedup --configs 64,256,1024 \
		--platform-label "1,2,4,8,10" \
		--figsize 9.0,5.2 \
		--dark

img/dycore_speedup.svg: runs/plot_dycore_scaling.py $(H100_RUNS:=/*) | img
	MPLBACKEND=$(MPLBACKEND) $(PYTHON) $< $(H100_RUNS) \
		-o $@ -q speedup --configs 64,256,1024 \
		--platform-label "1,2,4,8,10" \
		--figsize 6.8,4.4 \
		--dark

img:
	mkdir -p $@

deploy: index.html
	rm -rf $(DEPLOY_DIR)
	mkdir -p $(DEPLOY_DIR)/$(PRESENTATION)
	cp index.html $(DEPLOY_DIR)/$(PRESENTATION)/
	cp -a assets img reveal.js $(DEPLOY_DIR)/$(PRESENTATION)/

clean:
	rm -f index.html $(TITLE_FIGURE) $(ASYFIGURES) $(RESULT_FIGURES)
	rm -rf $(DEPLOY_DIR)

distclean: clean
	rm -rf reveal.js master.zip
