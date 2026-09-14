size(300);

real dx = 2.0;
real dy = 3.3;
real dz = 1.5;

int ni = 2;
int nj = 1;
int nk = 2;

pair iso(triple p)
{
    return (
        p.x - p.y,
        p.z + 0.5*(p.x + p.y)
    );
}

void edge(triple a, triple b)
{
    draw(iso(a)--iso(b), black+linewidth(0.8));
}

// Horizontal slices between neighboring grid cells.
real sliceGap = 0.12*dz;
path slice1 = iso((0,0,dz))--iso((ni*dx,0,dz))--iso((ni*dx,nj*dy,dz))--iso((0,nj*dy,dz))--cycle;
path slice2 = iso((0,0,dz+sliceGap))--iso((ni*dx,0,dz+sliceGap))--iso((ni*dx,nj*dy,dz+sliceGap))--iso((0,nj*dy,dz+sliceGap))--cycle;
fill(slice1, rgb(0.95,0.65,0.15)+opacity(0.45));
fill(slice2, rgb(0.95,0.65,0.15)+opacity(0.45));

// i-direction
for (int j=0; j<=nj; ++j)
for (int k=0; k<=nk; ++k)
    edge((0,j*dy,k*dz), (ni*dx,j*dy,k*dz));

// j-direction
for (int i=0; i<=ni; ++i) {
if (i == 1) continue;
for (int k=0; k<=nk; ++k)
    edge((i*dx,0,k*dz), (i*dx,nj*dy,k*dz));
}

// k-direction
for (int i=0; i<=ni; ++i) {
if (i == 1) continue;
for (int j=0; j<=nj; ++j)
    edge((i*dx,j*dy,0), (i*dx,j*dy,nk*dz));
}

draw(slice1, black+linewidth(0.8));
draw(slice2, black+linewidth(0.8));

label("$\mathsf{k=k_0}$", iso((1.55*dx,0.35*dy,dz+sliceGap)) + (0,-2), black+fontsize(16pt));
