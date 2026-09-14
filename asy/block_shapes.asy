size(900,0);

pen linePen = white+linewidth(0.8);
pen labelPen = white;

pair panelOffset(int n) { return (7.6*n, 0); }

pair iso(pair off, triple p)
{
    return off + (p.x - p.y, p.z + 0.5*(p.x + p.y));
}

void edge(pair off, triple a, triple b)
{
    draw(iso(off, a)--iso(off, b), linePen);
}

path face(pair off, triple a, triple b, triple c, triple d)
{
    return iso(off, a)--iso(off, b)--iso(off, c)--iso(off, d)--cycle;
}

void drawKBlock(pair off)
{
    real dx = 2.0;
    real dy = 3.3;
    real dz = 1.5;
    int ni = 2;
    int nj = 1;
    int nk = 2;

    real sliceGap = 0.12*dz;
    path slice1 = iso(off, (0,0,dz))--iso(off, (ni*dx,0,dz))--iso(off, (ni*dx,nj*dy,dz))--iso(off, (0,nj*dy,dz))--cycle;
    path slice2 = iso(off, (0,0,dz+sliceGap))--iso(off, (ni*dx,0,dz+sliceGap))--iso(off, (ni*dx,nj*dy,dz+sliceGap))--iso(off, (0,nj*dy,dz+sliceGap))--cycle;
    fill(slice1, rgb(0.95,0.65,0.15)+opacity(0.45));
    fill(slice2, rgb(0.95,0.65,0.15)+opacity(0.45));

    for (int j=0; j<=nj; ++j)
    for (int k=0; k<=nk; ++k)
        edge(off, (0,j*dy,k*dz), (ni*dx,j*dy,k*dz));

    for (int i=0; i<=ni; ++i) {
    if (i == 1) continue;
    for (int k=0; k<=nk; ++k)
        edge(off, (i*dx,0,k*dz), (i*dx,nj*dy,k*dz));
    }

    for (int i=0; i<=ni; ++i) {
    if (i == 1) continue;
    for (int j=0; j<=nj; ++j)
        edge(off, (i*dx,j*dy,0), (i*dx,j*dy,nk*dz));
    }

    draw(slice1, linePen);
    draw(slice2, linePen);
    label("$\mathsf{k=k_0}$", iso(off, (1.55*dx,0.35*dy,dz+sliceGap)) + (0,-2), labelPen+fontsize(16pt));
    label("$\mathsf{Layer\hbox{-}oriented\ block}$", off + (0.5, -1.0), labelPen+fontsize(14pt));
}

void drawJBlock(pair off)
{
    real dx = 2.0;
    real dy = 3.3;
    real dz = 3.0;
    int ni = 2;
    int nj = 1;
    int nk = 1;

    real sliceGap = 0.12*dx;
    path slice1 = iso(off, (dx,0,0))--iso(off, (dx,dy,0))--iso(off, (dx,dy,dz))--iso(off, (dx,0,dz))--cycle;
    path slice2 = iso(off, (dx+sliceGap,0,0))--iso(off, (dx+sliceGap,dy,0))--iso(off, (dx+sliceGap,dy,dz))--iso(off, (dx+sliceGap,0,dz))--cycle;
    fill(slice1, rgb(0.95,0.65,0.15)+opacity(0.45));
    fill(slice2, rgb(0.95,0.65,0.15)+opacity(0.45));

    for (int j=0; j<=nj; ++j)
    for (int k=0; k<=nk; ++k)
        edge(off, (0,j*dy,k*dz), (ni*dx,j*dy,k*dz));

    for (int i=0; i<=ni; ++i)
    for (int k=0; k<=nk; ++k)
        edge(off, (i*dx,0,k*dz), (i*dx,nj*dy,k*dz));

    for (int i=0; i<=ni; ++i)
    for (int j=0; j<=nj; ++j)
        edge(off, (i*dx,j*dy,0), (i*dx,j*dy,nk*dz));

    draw(slice1, linePen);
    draw(slice2, linePen);
    label("$\mathsf{j=j_0}$", iso(off, (dx+sliceGap,0,0)) + (-0.1,-0.1), SE, labelPen+fontsize(16pt));
    label("$\mathsf{Column\hbox{-}oriented\ block}$", off + (0.4, -1.0), labelPen+fontsize(14pt));
}

void drawGPUBlock(pair off)
{
    real dx = 2.0;
    real dy = 3.3;
    real dz = 3.0;
    int ni = 2;
    int nj = 1;
    int nk = 1;
    pen faceFill = rgb(0.95,0.65,0.15)+opacity(0.55);

    fill(face(off, (0,0,0), (ni*dx,0,0), (ni*dx,nj*dy,0), (0,nj*dy,0)), faceFill);
    fill(face(off, (0,0,0), (0,nj*dy,0), (0,nj*dy,nk*dz), (0,0,nk*dz)), faceFill);
    fill(face(off, (0,0,0), (ni*dx,0,0), (ni*dx,0,nk*dz), (0,0,nk*dz)), faceFill);
    fill(face(off, (ni*dx,0,0), (ni*dx,nj*dy,0), (ni*dx,nj*dy,nk*dz), (ni*dx,0,nk*dz)), faceFill);
    fill(face(off, (0,nj*dy,0), (ni*dx,nj*dy,0), (ni*dx,nj*dy,nk*dz), (0,nj*dy,nk*dz)), faceFill);
    fill(face(off, (0,0,nk*dz), (ni*dx,0,nk*dz), (ni*dx,nj*dy,nk*dz), (0,nj*dy,nk*dz)), faceFill);

    for (int j=0; j<=nj; ++j)
    for (int k=0; k<=nk; ++k)
        edge(off, (0,j*dy,k*dz), (ni*dx,j*dy,k*dz));

    for (int i=0; i<=ni; ++i) {
    if (i == 1) continue;
    for (int k=0; k<=nk; ++k)
        edge(off, (i*dx,0,k*dz), (i*dx,nj*dy,k*dz));
    }

    for (int i=0; i<=ni; ++i) {
    if (i == 1) continue;
    for (int j=0; j<=nj; ++j)
        edge(off, (i*dx,j*dy,0), (i*dx,j*dy,nk*dz));
    }

    label("$\mathsf{GPU\hbox{-}oriented\ block}$", off + (0.7, -1.0), labelPen+fontsize(14pt));
}

drawKBlock(panelOffset(0));
drawJBlock(panelOffset(1));
drawGPUBlock(panelOffset(2));
